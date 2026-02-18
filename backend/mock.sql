INSERT INTO jobs (id, status, user_id, model, file_name, secret_ref, result, result_error, result_received_at, result_token, public, created_at, started_at, finished_at)
VALUES (
    'd41ec6e6-3da7-4819-8055-826857a440c0',
    'succeeded',
    '71956291',
    'codex-gpt-5.2',
    'ICoveredMetavault.sol.zip',
    NULL,
    '{
        "vulnerabilities": [
            {
                "title": "Uninitialized UUPS proxy allows attacker to seize ownership and drain all assets",
                "impact": "A single missed/late initialization transaction during deployment results in total loss of all vault-held assets (the `asset()` token balance) because an attacker can seize ownership, upgrade the proxy, and/or reconfigure privileged roles to drain funds.",
                "summary": "If a proxy is deployed without atomically calling `initialize`, any account can initialize the vault, become the `OWNER_ROLE`, grant themselves operational roles, and ultimately upgrade or operate the vault to exfiltrate all tracked assets.",
                "severity": "High",
                "description": [
                    {
                        "desc": "`initialize(...)` is `public initializer` and grants `OWNER_ROLE` to `msg.sender` while setting the tracked `$.owner`. If a proxy is deployed and left uninitialized, the first external caller can become the owner and configure roles/state.",
                        "file": "audit/CoveredMetavault.sol",
                        "line_end": 192,
                        "line_start": 148
                    },
                    {
                        "desc": "Once initialized as owner, the attacker can authorize upgrades (`_authorizeUpgrade`) and deploy an implementation that transfers out all `asset()` tokens, or grant themselves `KEEPER_ROLE`/`MANAGER_ROLE` and abuse privileged flows.",
                        "file": "audit/CoveredMetavault.sol",
                        "line_end": 195,
                        "line_start": 194
                    }
                ],
                "remediation": "Ensure the proxy is initialized atomically at deployment (e.g., deploy via `ERC1967Proxy`/`TransparentUpgradeableProxy` with initializer calldata). Consider adding OpenZeppelin''s `onlyProxy` pattern to initializer entrypoints and enforce an explicit deployment process that cannot leave the proxy uninitialized.",
                "proof_of_concept": "1. Observe a freshly deployed proxy pointing to `CoveredMetavault` with `initialize` not called.\n2. Attacker calls `initialize(...)` with valid parameters and becomes `OWNER_ROLE`.\n3. Attacker calls `grantRole(KEEPER_ROLE, attacker)` / `grantRole(MANAGER_ROLE, attacker)` (admins set in `initialize`).\n4. Attacker upgrades the proxy to a malicious implementation via UUPS that transfers all `asset()` tokens to the attacker (or abuses privileged flows to extract value)."
            },
            {
                "title": "Permissionless matured redemption settlement enables premium-streaming manipulation and premium theft (platform revenue loss)",
                "impact": "The vault''s premium mechanism can be economically bypassed/discounted by untrusted users, causing the `premiumCollector` to receive materially less of the configured premium over time. This is a direct loss of platform assets (premium paid out of the vault''s tracked `asset()` balance), and it can also let redeemers exit having paid less premium than intended by keeping `lastPremiumTimestamp` close to `block.timestamp` through repeated permissionless calls.",
                "summary": "Any user can create many small redeem requests and, after the maturity delay, repeatedly call `settleMaturedRedemption()` to reset `lastPremiumTimestamp` at attacker-chosen intervals, reducing the effective premium streamed to `premiumCollector` and causing direct loss of platform assets (premium).",
                "severity": "High",
                "description": [
                    {
                        "desc": "`requestRedeem` explicitly allows small requests with no onchain minimum, noting that small requests can self-settle permissionlessly via `settleMaturedRedemption()`.",
                        "file": "audit/CoveredMetavault.sol",
                        "line_end": 538,
                        "line_start": 522
                    },
                    {
                        "desc": "`settleMaturedRedemption` is permissionless (any caller) and forces `_streamPremium()` before settling a matured request, giving untrusted users a direct lever to trigger premium streaming whenever they have a matured request available.",
                        "file": "audit/CoveredMetavault.sol",
                        "line_end": 855,
                        "line_start": 837
                    },
                    {
                        "desc": "`_streamPremium` computes premium based on `duration = now - lastPremiumTimestamp` and then **unconditionally sets** `$.lastPremiumTimestamp = nowTimestamp`. Because the premium model compounds per full year and is linear over partial years on the *current* `assetsAfter`, splitting a long interval into many short intervals reduces total premium streamed compared to a single call over the whole interval.",
                        "file": "audit/CoveredMetavault.sol",
                        "line_end": 1012,
                        "line_start": 956
                    }
                ],
                "remediation": "Make premium accrual **time-path independent** so that splitting calls does not change total premium (e.g., apply a single multiplicative decay factor based only on total elapsed time since the last stream using fixed-point exponentiation, or otherwise compute premium from a cumulative index). Alternatively, move premium streaming out of permissionless flows (or enforce a meaningful onchain minimum for permissionless settlement) so untrusted users cannot control premium update cadence.",
                "proof_of_concept": "Assume a non-zero `premiumRateBps` and a vault with significant `totalAssets()`.\n1. Attacker mints/obtains a small amount of metavault shares.\n2. Attacker submits many `requestRedeem` requests (each just large enough to avoid `ZeroAssets()` at settlement) over time.\n3. After `REDEEM_AUTO_CLAIMABLE_DELAY`, attacker calls `settleMaturedRedemption` for one request every few minutes/hours (or as frequently as they have matured requests), repeatedly triggering `_streamPremium()` with small `duration` and advancing `lastPremiumTimestamp`.\n4. Over the same wall-clock interval, the cumulative premium transferred to `premiumCollector` is strictly lower than if streaming occurred once (or infrequently) over the full interval."
            }
        ]
    }',
    NULL,
    '2026-01-23T07:34:39.742483Z',
    NULL,
    true,
    '2026-01-23T07:25:23.607368Z',
    '2026-01-23T07:25:24.261140Z',
    '2026-01-23T07:34:39.742483Z'
)
ON CONFLICT (id) DO UPDATE SET
    status = EXCLUDED.status,
    result = EXCLUDED.result,
    started_at = EXCLUDED.started_at,
    finished_at = EXCLUDED.finished_at;
