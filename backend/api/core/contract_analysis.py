import json
import re
from dataclasses import dataclass

import httpx
from fastapi import HTTPException
from loguru import logger

from api.core.config import settings
from api.schemas.contract_analysis import ContractAnalysisResponse, ContractEvidence, ContractVulnerability


SCORE_VERSION = 'risk-v1'
FUNCTION_NAME = 'submit_contract_analysis'
MAX_RESPONSE_TOKENS = 8_192
RESPONSE_RETRIES = 2
SEVERITY_ORDER = ('critical', 'high', 'medium', 'low', 'info')
SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}
SEVERITY_BANDS = {
    'critical': (90, 100),
    'high': (75, 89),
    'medium': (50, 74),
    'low': (20, 49),
    'info': (0, 19),
}
LEVEL_ANCHORS = {
    'critical': 95,
    'high': 80,
    'medium': 60,
    'low': 35,
    'info': 10,
}
CONFIDENCE_ANCHORS = {
    'high': 92,
    'medium': 72,
    'low': 48,
}
SEVERITY_WEIGHTS = {
    'critical': 1.00,
    'high': 0.85,
    'medium': 0.55,
    'low': 0.25,
    'info': 0.10,
}
LEVEL_PREFIX_MAP = {
    'critical': 'critical',
    'crit': 'critical',
    'high': 'high',
    'hi': 'high',
    'medium': 'medium',
    'med': 'medium',
    'low': 'low',
    'lo': 'low',
    'info': 'info',
    'inform': 'info',
}
CONFIDENCE_PREFIX_MAP = {
    'high': 'high',
    'hi': 'high',
    'medium': 'medium',
    'med': 'medium',
    'low': 'low',
    'lo': 'low',
}
SYSTEM_PROMPT = """
You are an expert smart contract security reviewer.

Analyze exactly one Solidity contract source file and identify realistic security vulnerabilities.
Focus on real security risk categories such as reentrancy, access control failures, authorization bypass,
accounting errors, unsafe external calls, privilege escalation, signature or nonce misuse, upgradeability bugs,
oracle or market manipulation issues, and other exploit paths that could materially harm users or assets.

Do not report:
- style issues
- gas optimizations
- naming or readability issues
- generic code smells without a plausible security consequence
- purely theoretical findings that are not realistically exploitable
- findings that require a trusted owner or admin to act maliciously

You must respond by calling the provided function.
Provide concise but specific summaries, remediation guidance, and line-based evidence.
If no meaningful vulnerabilities are present, return an empty vulnerabilities array.
""".strip()


@dataclass
class NormalizedEvidence:
    line_start: int
    line_end: int
    description: str


@dataclass
class NormalizedVulnerability:
    title: str
    severity: str
    impact_level: str
    exploitability_level: str
    confidence_level: str
    summary: str
    remediation: str
    evidence: list[NormalizedEvidence]


def _analysis_base_url() -> str:
    base_url = settings.BACKEND_CONTRACT_ANALYSIS_BASE_URL.rstrip('/')
    if base_url.endswith('/v1'):
        return base_url[:-3]
    return base_url


def _headers() -> dict[str, str]:
    return {
        'Authorization': f'Bearer {settings.BACKEND_CONTRACT_ANALYSIS_API_KEY.get_secret_value()}',
        'Content-Type': 'application/json',
    }


def _normalize_level(value: object) -> str:
    if not isinstance(value, str):
        return 'info'
    normalized = value.strip().lower()
    for prefix, result in LEVEL_PREFIX_MAP.items():
        if normalized.startswith(prefix):
            return result
    return 'info'


def _normalize_confidence(value: object) -> str:
    if not isinstance(value, str):
        return 'low'
    normalized = value.strip().lower()
    for prefix, result in CONFIDENCE_PREFIX_MAP.items():
        if normalized.startswith(prefix):
            return result
    return 'low'


def _normalize_line(value: object, *, default: int, line_count: int) -> int:
    if not isinstance(value, int):
        return default
    if value < 1:
        return 1
    if value > line_count:
        return line_count
    return value


def _clean_text(value: object, *, default: str) -> str:
    if not isinstance(value, str):
        return default
    text = value.strip()
    return text or default


def _title_key(title: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()


def _evidence_span(evidence: list[NormalizedEvidence]) -> tuple[int, int]:
    starts = [item.line_start for item in evidence]
    ends = [item.line_end for item in evidence]
    return min(starts, default=1), max(ends, default=1)


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return max(left[0], right[0]) <= min(left[1], right[1])


def _merge_text(preferred: str, fallback: str) -> str:
    if len(preferred) >= len(fallback):
        return preferred
    return fallback


def _merge_evidence(
    existing: list[NormalizedEvidence],
    incoming: list[NormalizedEvidence],
) -> list[NormalizedEvidence]:
    merged = {(item.line_start, item.line_end, item.description): item for item in existing}
    for item in incoming:
        merged[(item.line_start, item.line_end, item.description)] = item
    return sorted(merged.values(), key=lambda item: (item.line_start, item.line_end, item.description))


def _max_severity(*values: str) -> str:
    return min(values, key=lambda value: SEVERITY_RANK.get(value, len(SEVERITY_ORDER)))


def _normalize_evidence_items(items: object, *, line_count: int) -> list[NormalizedEvidence]:
    if not isinstance(items, list):
        return []

    evidence: list[NormalizedEvidence] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        start = _normalize_line(item.get('line_start'), default=1, line_count=line_count)
        end = _normalize_line(item.get('line_end'), default=start, line_count=line_count)
        if end < start:
            start, end = end, start
        description = _clean_text(item.get('description'), default='Security-relevant code path identified here.')
        evidence.append(NormalizedEvidence(line_start=start, line_end=end, description=description))
    return evidence


def _normalize_vulnerabilities(items: object, *, line_count: int) -> list[NormalizedVulnerability]:
    if not isinstance(items, list):
        return []

    normalized: list[NormalizedVulnerability] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        evidence = _normalize_evidence_items(item.get('evidence'), line_count=line_count)
        if not evidence:
            continue

        normalized.append(
            NormalizedVulnerability(
                title=_clean_text(item.get('title'), default='Unspecified security issue'),
                severity=_normalize_level(item.get('severity')),
                impact_level=_normalize_level(item.get('impact_level')),
                exploitability_level=_normalize_level(item.get('exploitability_level')),
                confidence_level=_normalize_confidence(item.get('confidence_level')),
                summary=_clean_text(
                    item.get('summary'),
                    default='The model identified a security issue in this contract.',
                ),
                remediation=_clean_text(
                    item.get('remediation'),
                    default='Review the affected code path and apply standard smart contract hardening practices.',
                ),
                evidence=evidence,
            )
        )
    return normalized


def _dedupe_vulnerabilities(vulnerabilities: list[NormalizedVulnerability]) -> list[NormalizedVulnerability]:
    deduped: list[NormalizedVulnerability] = []
    for candidate in vulnerabilities:
        candidate_key = _title_key(candidate.title)
        candidate_span = _evidence_span(candidate.evidence)
        merged = False
        for index, existing in enumerate(deduped):
            if _title_key(existing.title) != candidate_key:
                continue
            if not _spans_overlap(_evidence_span(existing.evidence), candidate_span):
                continue

            deduped[index] = NormalizedVulnerability(
                title=existing.title,
                severity=_max_severity(existing.severity, candidate.severity),
                impact_level=_max_severity(existing.impact_level, candidate.impact_level),
                exploitability_level=_max_severity(existing.exploitability_level, candidate.exploitability_level),
                confidence_level=(
                    'high'
                    if 'high' in {existing.confidence_level, candidate.confidence_level}
                    else 'medium'
                    if 'medium' in {existing.confidence_level, candidate.confidence_level}
                    else 'low'
                ),
                summary=_merge_text(existing.summary, candidate.summary),
                remediation=_merge_text(existing.remediation, candidate.remediation),
                evidence=_merge_evidence(existing.evidence, candidate.evidence),
            )
            merged = True
            break
        if not merged:
            deduped.append(candidate)
    return deduped


def _score_vulnerability(vulnerability: NormalizedVulnerability) -> tuple[int, int, int, int]:
    impact_score = LEVEL_ANCHORS[vulnerability.impact_level]
    exploitability_score = LEVEL_ANCHORS[vulnerability.exploitability_level]
    confidence_score = CONFIDENCE_ANCHORS[vulnerability.confidence_level]
    raw_score = round(0.45 * impact_score + 0.35 * exploitability_score + 0.20 * confidence_score)
    min_score, max_score = SEVERITY_BANDS[vulnerability.severity]
    risk_score = max(min_score, min(max_score, raw_score))
    return risk_score, impact_score, exploitability_score, confidence_score


def _overall_severity(score: int) -> str:
    if score >= 90:
        return 'critical'
    if score >= 75:
        return 'high'
    if score >= 45:
        return 'medium'
    if score >= 20:
        return 'low'
    return 'info'


def _compute_overall_risk(vulnerabilities: list[ContractVulnerability]) -> int:
    if not vulnerabilities:
        return 0

    top = max((vulnerability.risk_score / 100 for vulnerability in vulnerabilities), default=0.0)
    compound = 1.0
    high_or_higher = 0
    medium_or_higher = 0

    for vulnerability in vulnerabilities:
        risk = vulnerability.risk_score / 100
        compound *= 1 - SEVERITY_WEIGHTS[vulnerability.severity] * risk
        if vulnerability.risk_score >= 75:
            high_or_higher += 1
        if vulnerability.risk_score >= 50:
            medium_or_higher += 1

    compound = 1 - compound
    cluster_bonus = min(0.10, 0.03 * high_or_higher + 0.015 * max(0, medium_or_higher - 1))
    return round(100 * min(1.0, max(0.0, 0.55 * top + 0.35 * compound + cluster_bonus)))


def _fallback_overall_summary(vulnerabilities: list[ContractVulnerability]) -> str:
    if not vulnerabilities:
        return 'No meaningful security vulnerabilities were identified in the submitted Solidity contract.'

    titles = ', '.join(vulnerability.title for vulnerability in vulnerabilities[:3])
    return f'The contract appears risky due to: {titles}.'


def _tool_schema() -> dict:
    return {
        'type': 'function',
        'name': FUNCTION_NAME,
        'description': 'Return the final security analysis for this Solidity contract.',
        'parameters': {
            'type': 'object',
            'properties': {
                'overall_summary': {'type': 'string'},
                'vulnerabilities': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string'},
                            'severity': {'type': 'string'},
                            'impact_level': {'type': 'string'},
                            'exploitability_level': {'type': 'string'},
                            'confidence_level': {'type': 'string'},
                            'summary': {'type': 'string'},
                            'remediation': {'type': 'string'},
                            'evidence': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'line_start': {'type': 'integer'},
                                        'line_end': {'type': 'integer'},
                                        'description': {'type': 'string'},
                                    },
                                    'required': ['line_start', 'line_end', 'description'],
                                },
                            },
                        },
                        'required': [
                            'title',
                            'severity',
                            'impact_level',
                            'exploitability_level',
                            'confidence_level',
                            'summary',
                            'remediation',
                            'evidence',
                        ],
                    },
                },
            },
            'required': ['overall_summary', 'vulnerabilities'],
        },
    }


def _response_payload(*, source_code: str, model: str) -> dict:
    prompt = (
        f'{SYSTEM_PROMPT}\n\n'
        'Review the following Solidity contract source and report only meaningful security vulnerabilities. '
        'Return your final answer by calling the function tool.\n\n'
        '```solidity\n'
        f'{source_code}\n'
        '```'
    )
    return {
        'model': model,
        'input': prompt,
        'tools': [_tool_schema()],
        'max_output_tokens': MAX_RESPONSE_TOKENS,
    }


def _extract_function_arguments(payload: dict) -> dict:
    output = payload.get('output')
    if not isinstance(output, list):
        msg = 'Model response did not include output items'
        raise ValueError(msg)

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get('type') != 'function_call' or item.get('name') != FUNCTION_NAME:
            continue
        arguments = item.get('arguments')
        if not isinstance(arguments, str) or not arguments.strip():
            msg = 'Model function call did not include arguments'
            raise ValueError(msg)
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as err:
            msg = f'Model function call returned invalid JSON: {err}'
            raise ValueError(msg) from err
        if not isinstance(parsed, dict):
            msg = 'Model function call arguments must be a JSON object'
            raise ValueError(msg)
        return parsed

    msg = 'Model did not return the required function call'
    raise ValueError(msg)


def _validate_source_token_budget(token_count: int) -> None:
    max_tokens = settings.BACKEND_CONTRACT_ANALYSIS_MAX_SOURCE_TOKENS
    if token_count > max_tokens:
        msg = f'source_code exceeds max token budget: {token_count} > {max_tokens}'
        raise HTTPException(status_code=412, detail=msg)


async def _tokenize_source(*, client: httpx.AsyncClient, source_code: str, model: str) -> int:
    response = await client.post(
        f'{_analysis_base_url()}/tokenize',
        headers=_headers(),
        json={'model': model, 'prompt': source_code},
    )
    response.raise_for_status()
    payload = response.json()
    token_count = payload.get('count')
    if not isinstance(token_count, int):
        msg = 'Tokenize response did not include a valid token count'
        raise RuntimeError(msg)
    return token_count


async def _call_model(*, client: httpx.AsyncClient, source_code: str, model: str) -> dict:
    last_error: ValueError | None = None
    for attempt in range(RESPONSE_RETRIES):
        response = await client.post(
            f'{_analysis_base_url()}/v1/responses',
            headers=_headers(),
            json=_response_payload(source_code=source_code, model=model),
        )
        response.raise_for_status()
        try:
            return _extract_function_arguments(response.json())
        except ValueError as err:
            logger.warning(f'Invalid contract analysis function call on attempt {attempt + 1}: {err}')
            last_error = err

    msg = str(last_error or 'Model function call validation failed')
    raise HTTPException(status_code=502, detail=msg)


def _build_response(
    *,
    model: str,
    source_code: str,
    function_payload: dict,
) -> ContractAnalysisResponse:
    line_count = max(1, source_code.count('\n') + 1)
    vulnerabilities = _normalize_vulnerabilities(function_payload.get('vulnerabilities'), line_count=line_count)
    vulnerabilities = _dedupe_vulnerabilities(vulnerabilities)

    scored: list[ContractVulnerability] = []
    for vulnerability in vulnerabilities:
        risk_score, impact_score, exploitability_score, confidence_score = _score_vulnerability(vulnerability)
        scored.append(
            ContractVulnerability(
                id='',
                title=vulnerability.title,
                severity=vulnerability.severity,
                risk_score=risk_score,
                confidence_score=confidence_score,
                impact_score=impact_score,
                exploitability_score=exploitability_score,
                summary=vulnerability.summary,
                remediation=vulnerability.remediation,
                evidence=[
                    ContractEvidence(
                        line_start=item.line_start,
                        line_end=item.line_end,
                        description=item.description,
                    )
                    for item in vulnerability.evidence
                ],
            )
        )

    scored.sort(key=lambda vulnerability: (-vulnerability.risk_score, vulnerability.title.lower()))
    for index, vulnerability in enumerate(scored, start=1):
        vulnerability.id = f'V-{index:03d}'

    overall_risk_score = _compute_overall_risk(scored)
    overall_summary = _clean_text(function_payload.get('overall_summary'), default='')
    return ContractAnalysisResponse(
        model=model,
        score_version=SCORE_VERSION,
        overall_risk_score=overall_risk_score,
        overall_severity=_overall_severity(overall_risk_score),
        overall_summary=overall_summary or _fallback_overall_summary(scored),
        vulnerabilities=scored,
    )


async def analyze_contract(*, source_code: str, model: str) -> ContractAnalysisResponse:
    timeout = httpx.Timeout(settings.BACKEND_CONTRACT_ANALYSIS_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            token_count = await _tokenize_source(client=client, source_code=source_code, model=model)
            _validate_source_token_budget(token_count)
            function_payload = await _call_model(client=client, source_code=source_code, model=model)
        except HTTPException:
            raise
        except httpx.TimeoutException as err:
            raise HTTPException(status_code=504, detail='Contract analysis request timed out') from err
        except httpx.HTTPStatusError as err:
            detail = err.response.text.strip() or (
                f'Upstream model request failed with status {err.response.status_code}'
            )
            raise HTTPException(status_code=502, detail=detail) from err
        except Exception as err:  # noqa: BLE001
            logger.opt(exception=err).error('Contract analysis failed unexpectedly')
            raise HTTPException(status_code=502, detail='Contract analysis failed') from err

    return _build_response(model=model, source_code=source_code, function_payload=function_payload)
