{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  packages = [ pkgs.python3 pkgs.python3Packages.pip pkgs.ffmpeg pkgs.dejavu_fonts ];
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ];
  shellHook = ''
    test -d .venv || python -m venv .venv
    source .venv/bin/activate
    python -m pip install -q -r requirements.txt
    export ASCII_FONT="${pkgs.dejavu_fonts}/share/fonts/truetype/DejaVuSansMono.ttf"
  '';
}
