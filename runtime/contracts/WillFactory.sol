// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {WillController} from "./WillController.sol";

contract WillFactory {
    error ExistingLiveWill(address owner, address willContract, uint8 status);
    error ZeroAddress();

    address public immutable defaultWatcher;
    mapping(address owner => address willContract) public ownerToWill;

    event WillDeployed(
        address indexed owner,
        address indexed willContract,
        address indexed beneficiary,
        address watcher,
        uint256 triggerAfterSeconds
    );

    constructor(address defaultWatcher_) {
        if (defaultWatcher_ == address(0)) revert ZeroAddress();
        defaultWatcher = defaultWatcher_;
    }

    function createWill(address beneficiary, uint256 triggerAfterSeconds, address watcher) external returns (address willContract) {
        address existing = ownerToWill[msg.sender];
        if (existing != address(0)) {
            uint8 existingStatus = uint8(WillController(existing).status());
            if (
                existingStatus == uint8(WillController.WillStatus.Active)
                    || existingStatus == uint8(WillController.WillStatus.Triggered)
            ) {
                revert ExistingLiveWill(msg.sender, existing, existingStatus);
            }
        }

        address resolvedWatcher = watcher == address(0) ? defaultWatcher : watcher;
        WillController controller = new WillController();
        controller.initialize(msg.sender, beneficiary, triggerAfterSeconds, resolvedWatcher);

        willContract = address(controller);
        ownerToWill[msg.sender] = willContract;

        emit WillDeployed(msg.sender, willContract, beneficiary, resolvedWatcher, triggerAfterSeconds);
    }

    function getWillForOwner(address owner) external view returns (address) {
        return ownerToWill[owner];
    }
}
