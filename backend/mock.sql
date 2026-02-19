INSERT INTO jobs (id, status, user_id, model, file_name, secret_ref, result, result_error, result_received_at, result_token, public, created_at, started_at, finished_at)
VALUES (
    'd41ec6e6-3da7-4819-8055-826857a440c0',
    'succeeded',
    '71956291',
    'codex-gpt-5.2',
    'vault_program.zip',
    NULL,
    '{
        "vulnerabilities": [
            {
                "title": "missing signer check on withdraw instruction allows unauthorized fund extraction",
                "impact": "any user can drain all lamports from the vault by calling the withdraw instruction with the vault authority''s pubkey passed as an unsigned account. the program never verifies that the authority has actually signed the transaction, so the attacker only needs the publicly readable authority pubkey stored in the vault account data.",
                "summary": "the withdraw instruction handler does not enforce a signer check on the authority account, allowing any caller to withdraw funds by passing the correct authority pubkey without a valid signature.",
                "severity": "high",
                "description": [
                    {
                        "desc": "the `withdraw` instruction accepts the authority as a plain `AccountInfo` instead of using anchor''s `Signer` type. the handler transfers lamports from the vault to the recipient without verifying `authority.is_signer`, meaning any caller who knows the vault''s stored authority pubkey can invoke this instruction.",
                        "file": "audit/programs/vault/src/lib.rs",
                        "line_end": 58,
                        "line_start": 45
                    },
                    {
                        "desc": "the `Withdraw` accounts struct defines `authority` as `AccountInfo` rather than `Signer<''info>`. anchor''s automatic signer validation is bypassed, and no manual `require!(authority.is_signer)` check exists.",
                        "file": "audit/programs/vault/src/lib.rs",
                        "line_end": 92,
                        "line_start": 80
                    }
                ],
                "remediation": "change the authority field in the `Withdraw` accounts struct to use `Signer<''info>` so that anchor automatically enforces the signer check. alternatively, add a manual `require!(ctx.accounts.authority.is_signer, VaultError::Unauthorized)` check at the start of the instruction handler.",
                "proof_of_concept": "1. read the vault account data to obtain the stored authority pubkey.\n2. construct a withdraw instruction passing that pubkey as a non-signer account.\n3. set the recipient to the attacker''s wallet.\n4. submit the transaction — the program transfers all vault lamports to the attacker."
            },
            {
                "title": "unchecked account owner in reward claim allows redirection of staking rewards",
                "impact": "the staking program''s reward claim instruction does not validate that the destination token account belongs to the rightful staker. an attacker can pass their own token account as the reward destination, redirecting all pending reward tokens to themselves. repeated exploitation drains the entire reward pool.",
                "summary": "the `claim_rewards` instruction uses an unchecked `AccountInfo` for the reward destination token account. without verifying token::authority or token::mint constraints, any caller can substitute an arbitrary token account and steal rewards.",
                "severity": "high",
                "description": [
                    {
                        "desc": "the `reward_destination` account is accepted as `AccountInfo` and passed directly to a cpi `transfer` call without verifying its owner program, mint, or authority. this allows an attacker to pass a token account they control.",
                        "file": "audit/programs/staking/src/lib.rs",
                        "line_end": 128,
                        "line_start": 112
                    }
                ],
                "remediation": "use anchor''s `Account<''info, TokenAccount>` type with `token::mint` and `token::authority` constraints to validate the destination account belongs to the correct mint and is owned by the claiming user.",
                "proof_of_concept": "1. attacker stakes a minimum amount to obtain a valid staker pda.\n2. attacker calls `claim_rewards` passing their own token account as `reward_destination`.\n3. the program transfers reward tokens to the attacker''s account via cpi.\n4. attacker repeats for each reward epoch, draining the reward vault."
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
