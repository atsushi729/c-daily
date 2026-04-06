class CDaily < Formula
  desc "Claude Code daily log auto-generator"
  homepage "https://github.com/atsushi729/c-daily"
  url "https://github.com/atsushi729/c-daily/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"  # obtain with sha256sum after uploading gh release
  license "MIT"

  depends_on "python@3.11"

  def install
    libexec.install Dir["*"]

    # Rewrite shebang and path in bin/cdl
    (bin/"cdl").write <<~EOS
      #!/bin/bash
      export C_DAILY_LIB="#{libexec}/lib"
      exec "#{libexec}/bin/cdl" "$@"
    EOS
  end

  test do
    assert_match "cdl v", shell_output("#{bin}/cdl version")
  end
end

# --- Distribution as a Homebrew Tap ---
#
# 1. Create a homebrew-c-daily repository on GitHub:
#    https://github.com/atsushi729/homebrew-c-daily
#
# 2. Place this file as Formula/c-daily.rb
#
# 3. Create a tagged release:
#    git tag v0.1.0
#    git push origin v0.1.0
#
# 4. Update sha256:
#    curl -L https://github.com/atsushi729/c-daily/archive/refs/tags/v0.1.0.tar.gz | sha256sum
#
# 5. Users can then install with:
#    brew tap atsushi729/c-daily
#    brew install c-daily
