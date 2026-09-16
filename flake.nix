{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
      python = pkgs: pkgs.python3.withPackages (p: [ p.spacy p.spacy-models.en_core_web_sm ]);
      rust = pkgs: [ pkgs.cargo pkgs.rustc pkgs.gcc pkgs.git ];
    in {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell { packages = [ (python pkgs) ] ++ rust pkgs; };
      });

      apps = forAll (pkgs: {
        spacy = {
          type = "app";
          program = toString (pkgs.writeShellScript "nerbench-spacy" ''
            export PATH=${python pkgs}/bin:$PATH
            exec python3 ${./bench.py} "$@"
          '');
        };
        confidence = {
          type = "app";
          program = toString (pkgs.writeShellScript "nerbench-confidence" ''
            export PATH=${python pkgs}/bin:$PATH
            exec python3 ${./confidence.py} "$@"
          '');
        };
        resharp = {
          type = "app";
          program = toString (pkgs.writeShellScript "nerbench-resharp" ''
            export PATH=${pkgs.lib.makeBinPath (rust pkgs)}:$PATH
            export RUSTFLAGS="-C target-cpu=native"
            work=''${NERBENCH_DIR:-/tmp/nerbench}
            mkdir -p "$work"
            cp -rf --no-preserve=mode ${./resharp}/. "$work/resharp"
            cd "$work/resharp"
            if [ -n "''${RESHARP:-}" ]; then
              exec cargo run --release --quiet \
                --config "patch.crates-io.resharp.path=\"$RESHARP/resharp-engine\"" -- "$@"
            fi
            exec cargo run --release --quiet -- "$@"
          '');
        };
      });
    };
}
