# 단일 Solidity 리스크 분석 API 예시

이 문서는 `POST /v1/contracts/analyze` API를 바로 호출할 수 있도록 필요한 전제, 구동 순서, 요청/응답 스펙, 점수 산정법, `samples/Vault.sol` concrete example을 한 곳에 정리한 문서입니다.

## 1. 목적

- 입력: Solidity 소스코드 문자열 1개
- 출력: 취약점 리스트, 각 취약점의 `risk_score (0~100)`, 종합 `overall_risk_score (0~100)`
- 점수 방향: 숫자가 클수록 더 위험함

이 API는 기존 `jobs/*` 파이프라인과 별개인 동기 API입니다. 결과는 DB에 저장하지 않고, 요청 즉시 분석해서 바로 JSON으로 반환합니다.

## 2. 선행 조건

아래 예시는 다음 전제를 둡니다.

- 로컬 OpenAI-compatible `gpt-oss-120b` 서버가 `http://127.0.0.1:8000` 에서 실행 중
- 이 저장소 경로가 `/home/technoking/dev/evmbench`
- API 호출에는 프론트엔드가 필요 없고, backend stack과 `oai_proxy` 만 있으면 됨

## 3. 구동 순서

### 3-1. 로컬 모델 서버 확인

```bash
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
```

정상이라면 `gpt-oss-120b` 가 보여야 합니다.

### 3-2. backend + proxy stack 실행

```bash
cd /home/technoking/dev/evmbench/backend
docker compose --profile proxy up -d --build
```

### 3-3. backend 확인

```bash
curl -sS http://127.0.0.1:1337/v1/integration/frontend
```

예상 예시:

```json
{"auth_enabled":false,"key_predefined":true}
```

## 4. API 스펙

### 엔드포인트

```text
POST /v1/contracts/analyze
```

### 인증

- backend의 기존 인증 규칙을 그대로 따릅니다.
- 현재 로컬 구성처럼 auth가 꺼져 있으면 무인증 호출이 가능합니다.

### 요청 바디

```json
{
  "source_code": "pragma solidity ^0.8.23; ...",
  "model": "gpt-oss-120b"
}
```

필드 설명:

- `source_code`: 필수 문자열
- `model`: 선택 문자열, 생략 시 기본값 `gpt-oss-120b`

### 성공 응답

```json
{
  "model": "gpt-oss-120b",
  "score_version": "risk-v1",
  "overall_risk_score": 83,
  "overall_severity": "high",
  "overall_summary": "....",
  "vulnerabilities": [
    {
      "id": "V-001",
      "title": "....",
      "severity": "high",
      "risk_score": 89,
      "confidence_score": 92,
      "impact_score": 95,
      "exploitability_score": 80,
      "summary": "....",
      "remediation": "....",
      "evidence": [
        {
          "line_start": 42,
          "line_end": 45,
          "description": "...."
        }
      ]
    }
  ]
}
```

### 실패 응답

- `401`: 허용되지 않은 모델 또는 인증 실패
- `412`: 입력 검증 실패 또는 토큰 한도 초과
- `502`: 모델 함수 호출 실패 또는 응답 스키마 불일치
- `504`: 모델 호출 타임아웃

## 5. 토큰 한도

### 기본 한도

- `BACKEND_CONTRACT_ANALYSIS_MAX_SOURCE_TOKENS = 114688`

### 계산 근거

- 로컬 `gpt-oss-120b` 가 노출하는 컨텍스트 창: `131072`
- 이 중 `16384` 토큰은 다음 용도로 예약:
  - 시스템 프롬프트
  - 함수 스키마
  - 응답 생성 여유분
- 따라서 순수 `source_code` 예산:

```text
131072 - 16384 = 114688
```

### 실제 초과 시 실패 형태

예시:

```json
{"detail":"source_code exceeds max token budget: 132301 > 114688"}
```

## 6. 점수 산정법

## 6-1. 점수 방향

- 모든 점수는 `risk`
- `0`: 위험 거의 없음
- `100`: 매우 위험

## 6-2. 취약점별 점수

내부 anchor:

- severity band
  - `critical`: `90..100`
  - `high`: `75..89`
  - `medium`: `50..74`
  - `low`: `20..49`
  - `info`: `0..19`
- impact anchor
  - `critical=95`, `high=80`, `medium=60`, `low=35`, `info=10`
- exploitability anchor
  - `critical=95`, `high=80`, `medium=60`, `low=35`, `info=10`
- confidence anchor
  - `high=92`, `medium=72`, `low=48`

취약점별 산식:

```text
raw = 0.45*impact + 0.35*exploitability + 0.20*confidence
risk_score = round(raw)
risk_score 를 해당 severity band 안으로 clamp
```

응답에는 아래 4개 점수가 같이 내려옵니다.

- `risk_score`
- `impact_score`
- `exploitability_score`
- `confidence_score`

## 6-3. 종합 점수

종합 점수는 단순 평균이 아니라:

- 가장 위험한 취약점
- 취약점 누적 리스크
- 고위험 취약점 다발성

을 함께 반영합니다.

산식:

```text
top = max(risk_i / 100)

severity_weight:
critical=1.00
high=0.85
medium=0.55
low=0.25
info=0.10

compound = 1 - Π(1 - severity_weight_i * risk_i / 100)

cluster_bonus = min(
  0.10,
  0.03 * count(risk>=75) + 0.015 * max(0, count(risk>=50)-1)
)

overall_risk_score =
  round(100 * clamp(0.55*top + 0.35*compound + cluster_bonus, 0, 1))
```

종합 severity 구간:

- `90+`: `critical`
- `75..89`: `high`
- `45..74`: `medium`
- `20..44`: `low`
- `<20`: `info`

## 7. Vault.sol concrete example

### 7-1. 요청 JSON 만들기

```bash
cd /home/technoking/dev/evmbench
python3 - <<'PY'
import json
from pathlib import Path

payload = {
    "source_code": Path("samples/Vault.sol").read_text(),
}

Path("/tmp/evmbench_contract_request.json").write_text(
    json.dumps(payload),
    encoding="utf-8",
)
print("/tmp/evmbench_contract_request.json")
PY
```

### 7-2. API 호출

```bash
curl -sS \
  -H 'Content-Type: application/json' \
  --data @/tmp/evmbench_contract_request.json \
  http://127.0.0.1:1337/v1/contracts/analyze | python3 -m json.tool
```

### 7-3. 실제 응답 예시

아래는 `samples/Vault.sol` 에 대해 실제로 반환된 응답 예시입니다.

```json
{
  "model": "gpt-oss-120b",
  "score_version": "risk-v1",
  "overall_risk_score": 83,
  "overall_severity": "high",
  "overall_summary": "The Vault contract contains critical reentrancy vulnerability in the withdraw function and insecure access control using tx.origin in privileged functions, enabling phishing attacks and unauthorized treasury changes. Both issues can lead to loss of user funds or unauthorized control over contract assets.",
  "vulnerabilities": [
    {
      "id": "V-001",
      "title": "Reentrancy in withdraw() due to external call before state update",
      "severity": "high",
      "risk_score": 89,
      "confidence_score": 92,
      "impact_score": 95,
      "exploitability_score": 80,
      "summary": "The withdraw function sends Ether to the caller via a low-level call before updating the caller's balance. A malicious receiver can re-enter withdraw and repeatedly extract funds until the contract balance is exhausted.",
      "remediation": "Apply the Checks-Effects-Interactions pattern: update balance and nonce before the external call, or use a pull-payment model (e.g., store pending withdrawals and let users claim them). Consider using ReentrancyGuard.",
      "evidence": [
        {
          "line_start": 42,
          "line_end": 45,
          "description": "External call (.call) is performed before balance is reduced."
        },
        {
          "line_start": 46,
          "line_end": 48,
          "description": "State variables (balanceOf, nonceOf) are updated after the external call."
        }
      ]
    },
    {
      "id": "V-002",
      "title": "Improper authorization using tx.origin in changeTreasury() and emergencySweep()",
      "severity": "medium",
      "risk_score": 74,
      "confidence_score": 92,
      "impact_score": 80,
      "exploitability_score": 80,
      "summary": "Both privileged functions rely on `tx.origin == owner` for access control. A malicious contract can trick the owner into calling it, causing `tx.origin` to be the owner while `msg.sender` is the attacker contract, allowing unauthorized treasury changes or emergency sweeps.",
      "remediation": "Replace `tx.origin` checks with `msg.sender` and enforce proper role-based access control (e.g., Ownable). Ensure only the owner address can call these functions directly.",
      "evidence": [
        {
          "line_start": 53,
          "line_end": 57,
          "description": "changeTreasury uses tx.origin for authorization."
        },
        {
          "line_start": 60,
          "line_end": 64,
          "description": "emergencySweep also uses tx.origin for authorization."
        }
      ]
    }
  ]
}
```

### 7-4. 응답 읽는 법

- `overall_risk_score=83`
  - 이 계약 전체가 높은 위험 구간이라는 뜻입니다.
- `V-001 risk_score=89`
  - 재진입 이슈가 가장 위험한 취약점으로 판단되었다는 뜻입니다.
- `V-002 risk_score=74`
  - `tx.origin` 인증 오남용이 의미 있는 리스크지만, 재진입보다 약간 낮게 계산되었다는 뜻입니다.

## 8. 토큰 초과 재현 예시

```bash
cd /home/technoking/dev/evmbench
python3 - <<'PY'
import json
from pathlib import Path

source = Path("samples/Vault.sol").read_text()
big_source = "\n\n".join(source for _ in range(300))

Path("/tmp/evmbench_contract_request_too_large.json").write_text(
    json.dumps({"source_code": big_source}),
    encoding="utf-8",
)
print("/tmp/evmbench_contract_request_too_large.json")
PY

curl -sS \
  -H 'Content-Type: application/json' \
  --data @/tmp/evmbench_contract_request_too_large.json \
  http://127.0.0.1:1337/v1/contracts/analyze | python3 -m json.tool
```

예상 결과:

```json
{
  "detail": "source_code exceeds max token budget: 132301 > 114688"
}
```
