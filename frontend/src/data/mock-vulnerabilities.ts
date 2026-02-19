import type { Vulnerability } from "@/types"

export const MOCK_VULNERABILITIES: Vulnerability[] = [
  {
    id: "T-001",
    title: "markdown edge case testing",
    severity: "info",
    summary: `testing **bold**, *italic*, ~~strikethrough~~, and \`inline code\` in a single paragraph. also testing [links](https://example.com) and **\`bold code\`**.`,
    description: [
      {
        file: "programs/vault/src/lib.rs",
        line_start: 1,
        line_end: 3,
        desc: "test location for markdown testing.",
      },
    ],
    impact: `## headers test

### h3 header
#### h4 header
##### h5 header

## lists test

unordered list:
- item 1
- item 2 with \`inline code\`
- item 3 with **bold**
  - nested item a
  - nested item b

ordered list:
1. first item
2. second item
3. third item
   1. nested 3.1
   2. nested 3.2

## blockquote test

> this is a blockquote
> with multiple lines
>
> and a second paragraph in the quote

## table test

| column a | column b | column c |
|----------|----------|----------|
| cell 1   | cell 2   | cell 3   |
| \`code\` | **bold** | *italic* |

---

## mixed content

here's a paragraph with **bold text**, *italic text*, \`inline code\`, and a [link](https://example.com). testing **\`bold code\`** and *\`italic code\`*.`,
    proof_of_concept: `## code block tests

code block with language:

\`\`\`rust
use anchor_lang::prelude::*;

declare_id!("11111111111111111111111111111111");

#[program]
pub mod vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        ctx.accounts.vault.authority = ctx.accounts.authority.key();
        Ok(())
    }
}
\`\`\`

code block with typescript:

\`\`\`typescript
interface Props {
  name: string;
  value: number;
}

const Component = ({ name, value }: Props) => {
  return <div>{name}: {value}</div>;
};
\`\`\`

code block without language:

\`\`\`
plain text code block
no syntax highlighting
\`\`\`

inline code in a sentence: the \`withdraw()\` function calls \`transfer()\` via cpi internally.`,
    remediation: `## final tests

### horizontal rule

above the line

---

below the line

### long code line test

\`\`\`rust
pub const very_long_constant_name_for_testing_horizontal_scroll: u64 = 18_446_744_073_709_551_615;
\`\`\`

### complex nesting

1. **bold list item** with \`code\`
   - nested *italic* item
   - another nested item with [link](https://example.com)
2. regular item
   > blockquote inside list

### end of test`,
  },
  {
    id: "H-001",
    title: "missing signer check allows unauthorized fund withdrawal",
    severity: "high",
    summary: `the \`withdraw\` instruction does not verify that the \`authority\` account is a signer, allowing **any user** to drain funds from the vault by passing an arbitrary authority pubkey.`,
    description: [
      {
        file: "programs/vault/src/lib.rs",
        line_start: 45,
        line_end: 58,
        desc: "the withdraw instruction handler transfers lamports from the vault to the caller without verifying that the authority account has actually signed the transaction.",
      },
      {
        file: "programs/vault/src/lib.rs",
        line_start: 80,
        line_end: 92,
        desc: "the withdraw accounts struct uses `AccountInfo` for the authority field instead of `Signer`, bypassing anchor's automatic signer verification.",
      },
    ],
    impact: `any user can call the \`withdraw\` instruction and pass the vault's stored authority pubkey as an unsigned account, because the program never checks \`authority.is_signer\`:

- **all vault funds** can be drained in a single transaction
- the attacker only needs to know the vault's authority pubkey (which is stored on-chain and publicly readable)
- no special permissions or setup required`,
    proof_of_concept: `1. read the vault account data to obtain the stored \`authority\` pubkey
2. construct a \`withdraw\` instruction passing the authority pubkey as a non-signer account
3. set the \`recipient\` to the attacker's wallet
4. submit the transaction — the program transfers all vault lamports to the attacker`,
    remediation: `use anchor's \`Signer\` type for the authority account to enforce signature verification:

\`\`\`rust
#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut, has_one = authority)]
    pub vault: Account<'info, Vault>,
    pub authority: Signer<'info>,  // enforces is_signer check
    #[account(mut)]
    /// CHECK: recipient for lamports
    pub recipient: AccountInfo<'info>,
}
\`\`\``,
  },
  {
    id: "H-002",
    title: "pda seed collision enables account hijacking",
    severity: "high",
    summary: `the pda derivation for user accounts uses only the user's pubkey as a seed without domain separation between different instruction types, allowing a **seed collision** that lets an attacker hijack another user's account state.`,
    description: [
      {
        file: "programs/marketplace/src/lib.rs",
        line_start: 30,
        line_end: 42,
        desc: "the listing account pda is derived using only `[user.key().as_ref()]` without including a domain prefix like `b\"listing\"`, making it collide with the escrow account pda which uses the same seed pattern.",
      },
      {
        file: "programs/marketplace/src/lib.rs",
        line_start: 65,
        line_end: 75,
        desc: "the escrow account pda also uses `[user.key().as_ref()]` as its only seed, creating an identical derivation to the listing pda for the same user.",
      },
    ],
    impact: `because both the listing and escrow pdas derive from the same seeds, they resolve to the **same address**:

- a user who creates a listing can have their listing data overwritten when an escrow is initialized
- funds deposited into escrow can be withdrawn through the listing cancellation flow
- this effectively allows **theft of escrowed funds** by any user who has both a listing and an escrow`,
    proof_of_concept: `1. user a creates a listing, which initializes a pda at \`[user_a.key()]\`
2. user a also creates an escrow — the program attempts to init a pda at the same address
3. depending on instruction ordering, one account's data overwrites the other
4. user a can cancel the "listing" to reclaim funds that were actually deposited as escrow`,
    remediation: `add a unique domain prefix to each pda derivation to ensure no collisions between different account types:

\`\`\`rust
// listing pda
#[account(
    init,
    payer = user,
    space = 8 + Listing::INIT_SPACE,
    seeds = [b"listing", user.key().as_ref()],
    bump,
)]
pub listing: Account<'info, Listing>,

// escrow pda (different prefix)
#[account(
    init,
    payer = user,
    space = 8 + Escrow::INIT_SPACE,
    seeds = [b"escrow", user.key().as_ref()],
    bump,
)]
pub escrow: Account<'info, Escrow>,
\`\`\``,
  },
  {
    id: "H-003",
    title: "missing owner check on token account allows draining",
    severity: "high",
    summary: `the \`claim_rewards\` instruction does not validate the owner of the passed token account, allowing an attacker to substitute a **token account they control** and redirect reward tokens to themselves.`,
    description: [
      {
        file: "programs/staking/src/lib.rs",
        line_start: 112,
        line_end: 128,
        desc: "the reward_destination account is accepted as an unchecked `AccountInfo` and used directly as the destination for a token transfer cpi, without verifying its owner is the token program or that it belongs to the staker.",
      },
    ],
    impact: `an attacker can pass their own token account as the \`reward_destination\`:

| step | action | result |
|------|--------|--------|
| 1 | attacker stakes minimum tokens | gains valid staker pda |
| 2 | attacker calls claim_rewards with their own token account | rewards sent to attacker |
| 3 | repeat for each reward epoch | drains all reward tokens |

this results in **theft of all pending reward tokens** from the staking program.`,
    proof_of_concept: `\`\`\`rust
// attacker constructs the instruction with their own token account
let ix = claim_rewards(
    program_id,
    staker_pda,           // attacker's valid staker account
    attacker_token_acct,  // attacker's token account, not the expected one
    reward_mint,
    reward_vault,
);
// submit — program transfers rewards to attacker's token account
\`\`\``,
    remediation: `use anchor's \`Account\` type with a \`token::authority\` constraint to validate the token account:

\`\`\`rust
#[derive(Accounts)]
pub struct ClaimRewards<'info> {
    #[account(has_one = owner)]
    pub staker: Account<'info, StakerState>,
    pub owner: Signer<'info>,
    #[account(
        mut,
        token::mint = reward_mint,
        token::authority = owner,
    )]
    pub reward_destination: Account<'info, TokenAccount>,
    pub reward_mint: Account<'info, Mint>,
    #[account(mut)]
    pub reward_vault: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}
\`\`\``,
  },
]
