// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "./interfaces/IERC20.sol";
import {SafeERC20Lite} from "./lib/SafeERC20Lite.sol";

contract WillController {
    using SafeERC20Lite for IERC20;

    enum WillStatus {
        Active,
        Triggered,
        Cancelled,
        Claimed
    }

    error AlreadyInitialized();
    error ArrayEmpty();
    error InvalidTriggerSeconds(uint256 providedSeconds);
    error InvalidStatus(uint8 currentStatus);
    error NoNewTokens();
    error NotBeneficiary(address caller);
    error NotFactory(address caller);
    error NotOwner(address caller);
    error NotWatcher(address caller);
    error TooEarly(uint256 currentTimestamp, uint256 deadlineTimestamp);
    error UnauthorizedToken(address token);
    error ZeroAddress();

    uint256 public constant MAX_MONITOR_WINDOW_SECONDS = 7 days;
    uint256 public constant MIN_MONITOR_WINDOW_SECONDS = 30 seconds;
    uint256 public constant MIN_TRIGGER_SECONDS = 60 seconds;

    address public immutable factory;
    address public owner;
    address public beneficiary;
    address public watcher;
    uint64 public createdAt;
    uint64 public lastTriggerUpdateAt;
    uint32 public triggerAfterSeconds;
    uint32 public monitorWindowSeconds;
    bool public initialized;
    bytes32 public activityProofRef;
    WillStatus public status;

    address[] private _authorizedTokens;
    mapping(address token => bool isAuthorized) public tokenAuthorized;

    event WillInitialized(
        address indexed owner,
        address indexed beneficiary,
        address indexed watcher,
        uint256 triggerAfterSeconds,
        uint256 monitorWindowSeconds,
        uint256 deadlineTimestamp
    );
    event TokensRegistered(address indexed owner, address[] tokens);
    event BeneficiaryUpdated(address indexed owner, address indexed oldBeneficiary, address indexed newBeneficiary);
    event TriggerUpdated(
        address indexed owner,
        uint256 oldTriggerAfterSeconds,
        uint256 newTriggerAfterSeconds,
        uint256 monitorWindowSeconds,
        uint256 deadlineTimestamp
    );
    event WillTriggered(address indexed owner, address indexed beneficiary, bytes32 activityProofRef, uint256 triggeredAt);
    event Claimed(address indexed owner, address indexed beneficiary, address[] tokens);
    event Cancelled(address indexed owner, address indexed beneficiary);

    modifier onlyFactory() {
        if (msg.sender != factory) revert NotFactory(msg.sender);
        _;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner(msg.sender);
        _;
    }

    modifier onlyWatcher() {
        if (msg.sender != watcher) revert NotWatcher(msg.sender);
        _;
    }

    modifier onlyBeneficiary() {
        if (msg.sender != beneficiary) revert NotBeneficiary(msg.sender);
        _;
    }

    modifier onlyActive() {
        if (status != WillStatus.Active) revert InvalidStatus(uint8(status));
        _;
    }

    constructor() {
        factory = msg.sender;
    }

    function initialize(address owner_, address beneficiary_, uint256 triggerAfterSeconds_, address watcher_) external onlyFactory {
        if (initialized) revert AlreadyInitialized();
        if (owner_ == address(0) || beneficiary_ == address(0) || watcher_ == address(0)) revert ZeroAddress();
        if (triggerAfterSeconds_ < MIN_TRIGGER_SECONDS) revert InvalidTriggerSeconds(triggerAfterSeconds_);

        initialized = true;
        owner = owner_;
        beneficiary = beneficiary_;
        watcher = watcher_;
        createdAt = uint64(block.timestamp);
        lastTriggerUpdateAt = uint64(block.timestamp);
        triggerAfterSeconds = uint32(triggerAfterSeconds_);
        monitorWindowSeconds = _deriveMonitorWindowSeconds(triggerAfterSeconds_);
        status = WillStatus.Active;

        emit WillInitialized(owner_, beneficiary_, watcher_, triggerAfterSeconds_, monitorWindowSeconds, deadline());
    }

    function registerAuthorizedTokens(address[] calldata tokens) external onlyOwner onlyActive {
        _registerTokens(tokens);
    }

    function addAuthorizedTokens(address[] calldata tokens) external onlyOwner onlyActive {
        _registerTokens(tokens);
    }

    function updateBeneficiary(address newBeneficiary) external onlyOwner onlyActive {
        if (newBeneficiary == address(0)) revert ZeroAddress();

        address oldBeneficiary = beneficiary;
        beneficiary = newBeneficiary;

        emit BeneficiaryUpdated(owner, oldBeneficiary, newBeneficiary);
    }

    function updateTriggerAfterSeconds(uint256 newSeconds) external onlyOwner onlyActive {
        if (newSeconds < MIN_TRIGGER_SECONDS) revert InvalidTriggerSeconds(newSeconds);

        uint256 oldTriggerSeconds = triggerAfterSeconds;
        triggerAfterSeconds = uint32(newSeconds);
        monitorWindowSeconds = _deriveMonitorWindowSeconds(newSeconds);
        lastTriggerUpdateAt = uint64(block.timestamp);

        emit TriggerUpdated(owner, oldTriggerSeconds, newSeconds, monitorWindowSeconds, deadline());
    }

    function updateTriggerAfterDays(uint256 newDays) external onlyOwner onlyActive {
        if (newDays == 0) revert InvalidTriggerSeconds(newDays);
        _updateTriggerAfterSeconds(newDays * 1 days);
    }

    function cancelWill() external onlyOwner onlyActive {
        status = WillStatus.Cancelled;
        emit Cancelled(owner, beneficiary);
    }

    function markTriggered(bytes32 activityProofRef_) external onlyWatcher onlyActive {
        uint256 deadlineTimestamp = deadline();
        if (block.timestamp < deadlineTimestamp) revert TooEarly(block.timestamp, deadlineTimestamp);

        status = WillStatus.Triggered;
        activityProofRef = activityProofRef_;

        emit WillTriggered(owner, beneficiary, activityProofRef_, block.timestamp);
    }

    function claim(address[] calldata tokens) external onlyBeneficiary {
        if (status != WillStatus.Triggered) revert InvalidStatus(uint8(status));
        if (tokens.length == 0) revert ArrayEmpty();

        for (uint256 i = 0; i < tokens.length; ++i) {
            address token = tokens[i];
            if (!tokenAuthorized[token]) revert UnauthorizedToken(token);

            uint256 ownerBalance = IERC20(token).balanceOf(owner);
            if (ownerBalance == 0) {
                continue;
            }

            IERC20(token).safeTransferFrom(owner, beneficiary, ownerBalance);
        }

        status = WillStatus.Claimed;
        emit Claimed(owner, beneficiary, tokens);
    }

    function getWillConfig()
        external
        view
        returns (
            address owner_,
            address beneficiary_,
            uint256 createdAt_,
            uint256 lastTriggerUpdateAt_,
            uint256 triggerAfterSeconds_,
            uint256 monitorWindowSeconds_,
            address watcher_,
            uint8 status_,
            uint256 deadlineTimestamp_,
            bytes32 activityProofRef_
        )
    {
        return (
            owner,
            beneficiary,
            createdAt,
            lastTriggerUpdateAt,
            triggerAfterSeconds,
            monitorWindowSeconds,
            watcher,
            uint8(status),
            deadline(),
            activityProofRef
        );
    }

    function getAuthorizedTokens() external view returns (address[] memory) {
        return _authorizedTokens;
    }

    function deadline() public view returns (uint256) {
        return uint256(lastTriggerUpdateAt) + uint256(triggerAfterSeconds);
    }

    function _updateTriggerAfterSeconds(uint256 newSeconds) internal {
        if (newSeconds < MIN_TRIGGER_SECONDS) revert InvalidTriggerSeconds(newSeconds);

        uint256 oldTriggerSeconds = triggerAfterSeconds;
        triggerAfterSeconds = uint32(newSeconds);
        monitorWindowSeconds = _deriveMonitorWindowSeconds(newSeconds);
        lastTriggerUpdateAt = uint64(block.timestamp);

        emit TriggerUpdated(owner, oldTriggerSeconds, newSeconds, monitorWindowSeconds, deadline());
    }

    function _deriveMonitorWindowSeconds(uint256 triggerAfterSeconds_) internal pure returns (uint32) {
        uint256 derived = triggerAfterSeconds_ >= 14 days ? MAX_MONITOR_WINDOW_SECONDS : triggerAfterSeconds_ / 2;
        if (derived < MIN_MONITOR_WINDOW_SECONDS) {
            derived = MIN_MONITOR_WINDOW_SECONDS;
        }
        if (derived >= triggerAfterSeconds_) {
            derived = triggerAfterSeconds_ - 1;
        }
        return uint32(derived);
    }

    function _registerTokens(address[] calldata tokens) internal {
        if (tokens.length == 0) revert ArrayEmpty();

        uint256 added;
        for (uint256 i = 0; i < tokens.length; ++i) {
            address token = tokens[i];
            if (token == address(0)) revert ZeroAddress();
            if (tokenAuthorized[token]) {
                continue;
            }

            tokenAuthorized[token] = true;
            _authorizedTokens.push(token);
            unchecked {
                ++added;
            }
        }

        if (added == 0) revert NoNewTokens();
        emit TokensRegistered(owner, tokens);
    }
}
