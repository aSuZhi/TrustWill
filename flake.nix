{
  description = "OpenClaw-compatible plugin for the Agentic Wallet Will skill";

  outputs = { self, nixpkgs, ... }:
    let
      system = builtins.currentSystem;
      pkgs = import nixpkgs { inherit system; };
    in {
      openclawPlugin = {
        name = "agentic-wallet-will";
        skills = [ ./. ];
        packages = [
          pkgs.nodejs
          pkgs.python3
          pkgs.git
        ];
        needs = {
          stateDirs = [
            ".config/agentic-wallet-will"
            ".local/share/agentic-wallet-will"
          ];
          requiredEnv = [];
        };
      };
    };
}
