import type { Vulnerability } from "@/types"

export const MOCK_VULNERABILITIES: Vulnerability[] = [
  {
    id: "T-001",
    title: "Markdown Edge Case Testing",
    severity: "info",
    summary: `Testing **bold**, *italic*, ~~strikethrough~~, and \`inline code\` in a single paragraph. Also testing [links](https://example.com) and **\`bold code\`**.`,
    description: [
      {
        file: "src/Counter.sol",
        line_start: 1,
        line_end: 3,
        desc: "Test location for markdown testing.",
      },
    ],
    impact: `## Headers Test

### H3 Header
#### H4 Header
##### H5 Header

## Lists Test

Unordered list:
- Item 1
- Item 2 with \`inline code\`
- Item 3 with **bold**
  - Nested item A
  - Nested item B

Ordered list:
1. First item
2. Second item
3. Third item
   1. Nested 3.1
   2. Nested 3.2

## Blockquote Test

> This is a blockquote
> with multiple lines
>
> And a second paragraph in the quote

## Table Test

| Column A | Column B | Column C |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| \`code\` | **bold** | *italic* |

---

## Mixed Content

Here's a paragraph with **bold text**, *italic text*, \`inline code\`, and a [link](https://example.com). Testing **\`bold code\`** and *\`italic code\`*.`,
    proof_of_concept: `## Code Block Tests

Code block with language:

\`\`\`solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Test {
    uint256 public value;
    
    function setValue(uint256 _value) external {
        value = _value;
    }
}
\`\`\`

Code block with TypeScript:

\`\`\`typescript
interface Props {
  name: string;
  value: number;
}

const Component = ({ name, value }: Props) => {
  return <div>{name}: {value}</div>;
};
\`\`\`

Code block without language:

\`\`\`
plain text code block
no syntax highlighting
\`\`\`

Inline code in a sentence: The \`transfer()\` function calls \`_beforeTokenTransfer()\` internally.`,
    remediation: `## Final Tests

### Horizontal Rule

Above the line

---

Below the line

### Long Code Line Test

\`\`\`solidity
uint256 internal constant VERY_LONG_CONSTANT_NAME_FOR_TESTING_HORIZONTAL_SCROLL = 115792089237316195423570985008687907852837564279074904382605163141518161494337;
\`\`\`

### Complex Nesting

1. **Bold list item** with \`code\`
   - Nested *italic* item
   - Another nested item with [link](https://example.com)
2. Regular item
   > Blockquote inside list

### End of test`,
  },
  {
    id: "H-001",
    title: "Gauge weights queried with block numbers instead of timestamps",
    severity: "high",
    summary: `\`update_market\` uses **block numbers** as the time parameter for \`gauge_relative_weight_write\`, which expects weekly timestamps. This mismatch makes gauge weights resolve to zero and stops CANTO rewards from accruing.`,
    description: [
      {
        file: "src/Counter.sol",
        line_start: 7,
        line_end: 9,
        desc: "Rewards are computed per epoch derived from block heights and the same block number is passed to gauge_relative_weight_write.",
      },
      {
        file: "test/Counter.t.sol",
        line_start: 10,
        line_end: 12,
        desc: "Gauge weights are indexed by weekly timestamps; when provided with a block height, the controller looks up an empty timestamp bucket.",
      },
    ],
    impact: `Every call to \`update_market\` receives a **zero gauge weight**, causing:

- \`cantoReward\` stays zero
- \`accCantoPerShare\` never increases
- Lenders can never claim governance-funded CANTO emissions

This effectively **locks all rewards** in the contract permanently.`,
    proof_of_concept: `1. Governance whitelists a market and sets \`cantoPerBlock[epoch] = 1e18\`
2. Assign the market a positive gauge weight
3. After many blocks, a user calls \`claim()\`
4. \`update_market\` computes epoch from \`block.number\`
5. \`GaugeController\` treats this as a timestamp, rounds it where no points exist
6. Returns **0** instead of the expected weight`,
    remediation: `Query gauge weights using **weekly timestamps** rather than block heights:

\`\`\`solidity
uint256 weekTimestamp = (block.timestamp / WEEK) * WEEK;
uint256 weight = gaugeController.gauge_relative_weight_write(market, weekTimestamp);
\`\`\`

Align reward accounting to these timestamps so \`GaugeController\` reads populated weight checkpoints.`,
  },
  {
    id: "H-002",
    title: "Unchecked return value in token transfer",
    severity: "high",
    summary: `The contract does not check the return value of ERC20 \`transfer\` calls, allowing **silent failures** that can lead to accounting mismatches.`,
    description: [
      {
        file: "src/Counter.sol",
        line_start: 11,
        line_end: 14,
        desc: "Token transfer return value is not checked, some tokens return false on failure instead of reverting.",
      },
    ],
    impact: `Users may believe tokens were transferred when they were not, leading to:

- **Loss of funds** for users
- **Protocol insolvency** due to accounting mismatches
- Potential for griefing attacks`,
    proof_of_concept: `1. Deploy with a token that returns \`false\` on failed transfers (e.g., some USDT implementations)
2. Call \`deposit()\` with insufficient allowance
3. The transfer fails silently but the user's balance is credited
4. User can now withdraw more than they deposited`,
    remediation: `Use OpenZeppelin's \`SafeERC20\` library:

\`\`\`solidity
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

using SafeERC20 for IERC20;

token.safeTransfer(recipient, amount);
token.safeTransferFrom(sender, recipient, amount);
\`\`\``,
  },
  {
    id: "H-003",
    title: "Reentrancy in withdrawal function",
    severity: "high",
    summary: `State updates occur **after** external calls, allowing malicious contracts to re-enter and drain funds. This is a classic reentrancy vulnerability.`,
    description: [
      {
        file: "script/Counter.s.sol",
        line_start: 8,
        line_end: 14,
        desc: "External call is made before state is updated, creating a reentrancy window.",
      },
    ],
    impact: `An attacker can recursively call \`withdraw()\` before their balance is set to zero, **draining all contract funds**.

| Attack Step | Balance | Contract ETH |
|-------------|---------|--------------|
| Initial | 1 ETH | 10 ETH |
| 1st withdraw | 1 ETH | 9 ETH |
| 2nd withdraw (reentrant) | 1 ETH | 8 ETH |
| ... | ... | ... |
| Final | 0 ETH | 0 ETH |`,
    proof_of_concept: `\`\`\`solidity
contract Attacker {
    Victim victim;
    
    function attack() external payable {
        victim.deposit{value: 1 ether}();
        victim.withdraw();
    }
    
    receive() external payable {
        if (address(victim).balance >= 1 ether) {
            victim.withdraw(); // Re-enter before balance update
        }
    }
}
\`\`\``,
    remediation: `Follow the **checks-effects-interactions** pattern:

\`\`\`solidity
function withdraw() external {
    uint256 amount = balances[msg.sender];
    require(amount > 0, "No balance");
    
    // Effect: Update state BEFORE external call
    balances[msg.sender] = 0;
    
    // Interaction: External call AFTER state update
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
}
\`\`\`

Alternatively, use OpenZeppelin's \`ReentrancyGuard\`.`,
  },
]
