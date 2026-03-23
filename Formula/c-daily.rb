class CDaily < Formula
  desc "Claude Code 日次ログ自動生成ツール"
  homepage "https://github.com/Atsushi Hatakeyama/c-daily"
  url "https://github.com/Atsushi Hatakeyama/c-daily/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"  # gh release upload 後に sha256sum で取得
  license "MIT"

  depends_on "python@3.11"

  def install
    libexec.install Dir["*"]

    # bin/c-daily のシェバンとパスを書き換え
    (bin/"c-daily").write <<~EOS
      #!/bin/bash
      export C_DAILY_LIB="#{libexec}/lib"
      exec bash "#{libexec}/bin/c-daily" "$@"
    EOS
  end

  test do
    assert_match "c-daily v", shell_output("#{bin}/c-daily version")
  end
end

# --- Homebrew Tap としての配布方法 ---
#
# 1. GitHub に homebrew-c-daily リポジトリを作成
#    https://github.com/Atsushi Hatakeyama/homebrew-c-daily
#
# 2. このファイルを Formula/c-daily.rb として配置
#
# 3. タグ付きリリースを作成:
#    git tag v0.1.0
#    git push origin v0.1.0
#
# 4. sha256 を更新:
#    curl -L https://github.com/Atsushi Hatakeyama/c-daily/archive/refs/tags/v0.1.0.tar.gz | sha256sum
#
# 5. ユーザーはこれだけでインストールできる:
#    brew tap Atsushi Hatakeyama/c-daily
#    brew install c-daily
