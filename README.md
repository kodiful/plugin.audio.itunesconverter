# Kodiアドオン：iTunesプレイリストコンバータ

iTunesプレイリストコンバータは、iTunesが出力するライブラリを、Kodiのプレイリストファイル（m3uファイル）に変換する機能、および、HTMLファイルに変換する機能を提供します。[itunestom3u](https://code.google.com/p/itunestom3u/)を参考にしました。

アドオン設定画面の「一般設定」「HTML変換設定」で設定を行った後、アドオンを起動すると、一般設定、HTML変換設定にしたがって変換を開始します。
変換はバックグラウンドで実行され、実行が完了すると画面に通知されます。処理対象が大量にある場合は、変換に数分かかることがあります。
「実行」の都度、古いファイルは削除され、新しいファイルが生成されます。

アドオン設定画面では、以下にしたがって設定してください。

## 一般設定

![アドオン設定画面（一般設定）](https://github.com/kodiful/plugin.audio.itunesconverter/assets/12268536/33836727-3065-404f-85f2-a89daf8d3e95)

### ライブラリ.xmlへのパス

iTunesライブラリ（xmlファイル）へのパスを設定してください。
xmlファイルは、iTunesのメニューで、ファイル→ライブラリ→ライブラリを書き出し… を選択して出力できます。
デフォルトのファイル名は、ライブラリ.xml です（macOSの以前のiTunesでは、/Users/(username)/Music/iTunes/iTunes Music Library.xml に自動出力されていました）。
アドオンは、ここで設定したxmlファイルを解析して変換処理を行います。

### ファイルパスを変換する

Kodiのプレイリストファイル（m3uファイル）に出力するコンテンツのファイルパスの形式が、ライブラリ.xmlに記述されているファイルパスの形式と異なる場合（ファイルパスの文字列を一部他の文字列と置換する必要がある場合）は、これをチェックしてください。

### 変換前のパス、変換後のパス

置換すべき文字列の部分と、これを置換する文字列をそれぞれ設定してください。
私の環境では、以下の設定で変換ができていますが、OSやiTunesのバージョン、iTunesの設定で差異があるかもしれないので注意してください。

|OS|変換前のパス|変換後のパス|
|:---|:---|:---|
|Windows 7|file://localhost/||
|Windows 10|file://localhost/||
|macOS|file://||


***

## HTML変換設定

![アドオン設定画面（HTML変換設定）](https://github.com/kodiful/plugin.audio.itunesconverter/assets/12268536/eb2bdc25-c649-4dc3-9b62-7ed3f7477825)

### プレイリストをHTMLに変換する

生成するHTMLのタイプに応じて設定値を選択してください。

|設定値|生成するHTMLのタイプ|生成例|
|:---|:---|:---|
|none（デフォルト）|HTMLを生成しない||
|separated|プレイリスト毎にHTMLを生成する|![separated](https://github.com/kodiful/plugin.audio.itunesconverter/assets/12268536/f2b88571-d4fb-4929-9e3d-77d770aa1184)|
|combined|すべてをツリーとして一つのHTMLを生成する|![combined](https://github.com/kodiful/plugin.audio.itunesconverter/assets/12268536/102e77ce-7ecf-4b9a-a84b-a8c9f4d57996)|

### HTMLプレイリストのディレクトリへのパス

生成されたHTMLファイルを書き込むパス（separatedを選択した場合はルートディレクトリのパス）を設定してください。
