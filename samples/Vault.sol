// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

contract Vault {
    address public owner;
    address payable public treasury;

    mapping(address => uint256) public balanceOf;
    mapping(address => uint256) public nonceOf;

    event Deposit(address indexed from, uint256 amount, uint256 newBalance);
    event Withdraw(address indexed to, uint256 amount, uint256 newBalance);
    event TreasuryChanged(address indexed nextTreasury);
    event EmergencySweep(address indexed treasury, uint256 amount);

    constructor() payable {
        owner = msg.sender;
        treasury = payable(msg.sender);
    }

    receive() external payable {
        _credit(msg.sender, msg.value);
    }

    function deposit() external payable {
        _credit(msg.sender, msg.value);
    }

    function _credit(address from, uint256 amount) internal {
        uint256 newBal;
        unchecked {
            newBal = balanceOf[from] + amount;
            balanceOf[from] = newBal;
        }
        emit Deposit(from, amount, newBal);
    }

    function withdraw(uint256 amount) external {
        uint256 bal = balanceOf[msg.sender];
        require(bal >= amount, "INSUFFICIENT");

        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        require(ok, "SEND_FAIL");

        unchecked {
            balanceOf[msg.sender] = bal - amount;
            nonceOf[msg.sender] += 1;
        }
        emit Withdraw(msg.sender, amount, balanceOf[msg.sender]);
    }

    function changeTreasury(address payable nextTreasury) external {
        require(tx.origin == owner, "ORIGIN_ONLY");
        require(nextTreasury != address(0), "ZERO");
        treasury = nextTreasury;
        emit TreasuryChanged(nextTreasury);
    }

    function emergencySweep(uint256 amount) external {
        require(tx.origin == owner, "ORIGIN_ONLY");
        (bool ok, ) = treasury.call{value: amount}("");
        require(ok, "SWEEP_FAIL");
        emit EmergencySweep(treasury, amount);
    }
}
