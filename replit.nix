{pkgs}: {
  deps = [
    pkgs.gettext
    pkgs.postgresql
    pkgs.libxcrypt
    pkgs.glibcLocales
  ];
}
