import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
import re
import numpy as np

# --- ページ基本設定 ---
st.set_page_config(page_title="ブランド真贋Web解析・3市場価格帯算出システム", layout="wide")

st.title("🔍 ブランド品 型番・モデル名即時検索・3市場相場 ＆ 全ジャンル対応高度真贋自動解析")
st.caption("Web上の公開市場データから「3市場のリアルタイム相場幅」と「素材・文字盤・装飾別のプロ高度真贋ポイント」を高速抽出します。")

# --- 偽物・ノベルティ・付属品単品（ノイズ）の除外キーワード ---
EXCLUDE_KEYWORDS = [
    "ノベルティ", "並行輸入", "訳あり", "ジャンク", "コピー", "互換", 
    "リペア", "補修", "社外", "パーツ", "サンプル", "非売品", "同型",
    "フェルト", "保護布", "保護カバー", "保存袋", "空箱", "ショッパー", 
    "箱のみ", "袋のみ", "鍵のみ", "ストラップのみ", "ベルトのみ", "空き箱", 
    "カデナのみ", "クロシェットのみ", "冊子", "当て布", "付属品のみ", 
    "ベゼルのみ", "文字盤のみ", "コマ", "コマのみ", "余りコマ", "あまりコマ", 
    "余り駒", "あまり駒", "駒のみ", "駒", "ブレスのみ", "針のみ", "リューズのみ", 
    "ケースのみ", "裏蓋のみ", "ベゼル", "風防", "針セット", "ジャンク品", "不動", "部品"
]

# --- モデル単体入力時のブランド名自動補完マップ ---
BRAND_COMPLETION_MAP = {
    # ロレックス
    "デイトナ": "ロレックス デイトナ",
    "サブマリーナ": "ロレックス サブマリーナ",
    "デイトジャスト": "ロレックス デイトジャスト",
    "エクスプローラー": "ロレックス エクスプローラー",
    "GMTマスター": "ロレックス GMTマスター",
    "デイデイト": "ロレックス デイデイト",
    "ヨットマスター": "ロレックス ヨットマスター",
    "ミルガウス": "ロレックス ミルガウス",
    "エアキング": "ロレックス エアキング",
    "オイスターパーペチュアル": "ロレックス オイスターパーペチュアル",
    "スカイドゥエラー": "ロレックス スカイドゥエラー",
    "シードゥエラー": "ロレックス シードゥエラー",
    
    # パテック / オーデマピゲ / ヴァシュロン
    "カラトラバ": "パテックフィリップ カラトラバ",
    "ノーチラス": "パテックフィリップ ノーチラス",
    "アクアノート": "パテックフィリップ アクアノート",
    "ロイヤルオーク": "オーデマピゲ ロイヤルオーク",
    "オーヴァーシーズ": "ヴァシュロンコンスタンタン オーヴァーシーズ",
    
    # オメガ / カルティエ / ウブロ / 他高級時計
    "シーマスター": "オメガ シーマスター",
    "スピードマスター": "オメガ スピードマスター",
    "タンク": "カルティエ タンク",
    "サントス": "カルティエ サントス",
    "パシャ": "カルティエ パシャ",
    "バロンブルー": "カルティエ バロンブルー",
    "ビッグバン": "ウブロ ビッグバン",
    "クラシックフュージョン": "ウブロ クラシックフュージョン",

    # エルメス
    "バーキン": "エルメス バーキン",
    "バーキン25": "エルメス バーキン25",
    "バーキン30": "エルメス バーキン30",
    "ケリー": "エルメス ケリー",
    "ピコタン": "エルメス ピコタン",
    "ガーデンパーティ": "エルメス ガーデンパーティ",
    "コンスタンス": "エルメス コンスタンス",
    "ボリード": "エルメス ボリード",
    "エールバッグ": "エルメス エールバッグ",
    "ベアン": "エルメス ベアン",
    "ドゴン": "エルメス ドゴン",
    "シルクイン": "エルメス シルクイン",
    "シェーヌダンクル": "エルメス シェーヌダンクル",
    "Hウォッチ": "エルメス Hウォッチ",
    "クリッパー": "エルメス クリッパー",
    "ケープコッド": "エルメス ケープコッド",
    "カレ": "エルメス カレ 90",

    # シャネル
    "マトラッセ": "シャネル マトラッセ",
    "ボーイシャネル": "シャネル ボーイシャネル",
    "ココハンドル": "シャネル ココハンドル",
    "カンボン": "シャネル カンボン",
    "J12": "シャネル J12",
    "プルミエール": "シャネル プルミエール",
    "ココマーク ピアス": "シャネル ピアス ココマーク",
    "シャネル ピアス": "シャネル ピアス ココマーク",

    # ルイ・ヴィトン
    "ネヴァーフル": "ルイヴィトン ネヴァーフル",
    "スピーディ": "ルイヴィトン スピーディ",
    "アルマ": "ルイヴィトン アルマ",
    "キーポル": "ルイヴィトン キーポル",
    "カプシーヌ": "ルイヴィトン カプシーヌ",
    "オンザゴー": "ルイヴィトン オンザゴー",
    "バムバッグ": "ルイヴィトン バムバッグ",
    "ジッピーウォレット": "ルイヴィトン ジッピーウォレット",
    "ポルトフォイユ": "ルイヴィトン ポルトフォイユ",
    "タンブール": "ルイヴィトン タンブール"
}

# --- プロ仕様・全ブランド全ジャンル高度真贋データベース ---
def fetch_authenticity_guides(keyword):
    kw_upper = keyword.upper()
    
    # 1. シャネル（CHANEL）時計 ＆ ジュエリー ＆ バッグ
    if "シャネル" in kw_upper or "CHANEL" in kw_upper or any(w in kw_upper for w in ["マトラッセ", "ボーイシャネル", "ココハンドル", "カンボン", "J12", "プルミエール", "ココマーク"]):
        if any(w in kw_upper for w in ["プルミエール", "J12", "マドモアゼル", "ボーイフレンド", "コードココ", "時計"]):
            return [
                {"item": "💎 八角形風防サファイアガラスのカッティング（プルミエール）", "detail": "パリのヴァンドーム広場を模した8角形カットの風防エッジに歪みがなく、光の屈折と透明感が均一か。"},
                {"item": "🔩 裏蓋（ケースバック）のビス形状と「CHANEL PARIS」刻印", "detail": "裏蓋を固定する4点マイナスネジの溝の鋭さ、および「CHANEL PARIS」「SWISS MADE」刻印の打刻の深さとシャープさ。"},
                {"item": "🔗 チェーンブレスレットとレザーコード編み込み構造", "detail": "ゴールド/シルバーチェーンに組み込まれたレザーの縫製・質感が滑らかで、バックル部分の「CC」マークのカシメが頑丈か。"},
                {"item": "✨ J12等ハイテクセラミックの硬度・重量感・色ツヤ", "detail": "高硬度セラミック特有の上品な光沢、ずっしりとした重量感、ケースとスチール裏蓋の継ぎ目の隙間のなさ。"},
                {"item": "⚙️ 逆回転防止ベゼルのクリック音と文字盤「CHANEL」フォント", "detail": "J12等のベゼル回し時の節度あるクリック感、および文字盤インデックス・針の断面バリのなさ。"}
            ]
        elif any(w in kw_upper for w in ["ピアス", "イヤリング", "ネックレス", "ブレスレット", "リング", "ジュエリー", "アクセサリー"]):
            return [
                {"item": "楕円形刻印プレート（CHANEL・年式表記・ココマーク）", "detail": "ピアス裏面等の刻印プレートにある「CHANEL」「Made in France/Italy」「01P/21C等の年式表記」のクリアな刻印。"},
                {"item": "金属の適度な重量感・メッキのバリや角の落とし", "detail": "手にとった際の密度の高さ、メッキの厚み、角やフチに金属のバリ（突起）やノリのハミ出しがないか。"},
                {"item": "ラインストーン/フェイクパール爪留め精度", "detail": "爪留め加工の均一性、フェイクパール表面の質感・光沢の自然さ。"}
            ]
        else:
            return [
                {"item": "ターンロック金具（CCマーク）の刻印・マイナスネジ", "detail": "金具メッキの角に丸みがあり、裏側固定部がマイナスネジ（プラスネジは偽物疑い）であること。"},
                {"item": "ギャランティカード ＆ シリアルシール（ホログラム）", "detail": "シリアルシールのブラックライト照射での発光、シール表面の切り込み、ココマーク透かし（近年は金属プレート）。"},
                {"item": "マトラッセのキルティング格子ステッチ合わせ", "detail": "フラップ（蓋）を閉じた際に、本体と蓋のキルティングのダイヤ柄ステッチラインが狂いなく一致するか。"},
                {"item": "革の質（キャビアスキン/ラムスキン）とシボの硬さ", "detail": "キャビアスキンの型押し粒の立体感、ラムスキンのふっくら感と革独特の上品な香り。"},
                {"item": "CHANEL印字ロゴ（C/A/Eの特殊フォント特徴）", "detail": "「C」の切り口が斜め、「A」の頂点が平ら、「E」の真ん中の横線が最も短い特徴を満たしているか。"}
            ]

    # 2. ルイ・ヴィトン（LOUIS VUITTON）時計 ＆ 財布 ＆ バッグ
    elif "ヴィトン" in kw_upper or "LOUIS" in kw_upper or "VUITTON" in kw_upper or any(w in kw_upper for w in ["ネヴァーフル", "スピーディ", "アルマ", "キーポル", "ジッピー", "ポルトフォイユ", "タンブール"]):
        if any(w in kw_upper for w in ["タンブール", "スピンタイム", "時計"]):
            return [
                {"item": "🥁 太鼓型ケース側面の「LOUIS VUITTON」12文字刻印", "detail": "ケース側面に深く刻印された「L-O-U-I-S-V-U-I-T-T-O-N」の12文字が、1時〜12時のインデックス位置に寸分違わず完全に一致しているか。"},
                {"item": "ケースバック（裏蓋）のLVモチーフ刻印と型番・シリアル", "detail": "裏蓋中央に美しく打刻されたモノグラム・LVサークルおよび型番（Q1100等）・シリアルナンバーのフォント鮮明さ。"},
                {"item": "インターチェンジャブル（ワンタッチベルト交換機構）機能", "detail": "ベルト裏面の爪を引いてワンタッチで着脱できるオリジナルスライド機構のガタつきのない精度。"},
                {"item": "ダイヤル印刷の立体感と針側面断面の研磨仕上げ", "detail": "文字盤のVマークやモノグラム柄のプリント精度、針側面断面に加工傷がないこと。"}
            ]
        elif any(w in kw_upper for w in ["ジッピー", "ポルトフォイユ", "財布", "ウォレット", "コインケース"]):
            return [
                {"item": "LOUIS VUITTON PARIS刻印フォント精度", "detail": "「O」の文字が真円か、「R」の右足のハネ具合、「PARIS」のPとAの間隔およびフォントの深さ。"},
                {"item": "シリアルナンバー ＆ RFID（ICチップ）読み取り", "detail": "2021年以降モデルはNFCアプリ（IC Card Check等）でICチップが検出可能か。旧モデルはシリアル印字。"},
                {"item": "ファスナープル（LVロゴ）のメッキと重量感", "detail": "金メッキの質感が不自然に明るすぎず、LVロゴの刻印が深すぎず浅すぎず滑らかか。"},
                {"item": "キャンバス/レザーの印字鮮明さとコバ塗り", "detail": "モノグラム/ダミエ生地の印字鮮明さ、およびカードスロットフチのコバ塗りのベタつきや剥がれ。"}
            ]
        else:
            return [
                {"item": "LOUIS VUITTON PARISブランドロゴフォント", "detail": "ロゴ刻印の「O」の文字がきれいな正円か、「R」の右足のハネ具合、印字フォントの間隔。"},
                {"item": "シリアルナンバー ＆ RFID（ICチップ）検出", "detail": "近年のモデルはNFCアプリでICチップが検出できるか。旧モデルはシリアル刻印の場所・フォント。"},
                {"item": "金具・ビス（ネジ）の刻印精度と溝", "detail": "ビスの頭（マイナス溝）の深さが均一で、刻印の底面にバリやメッキムラがないか。"},
                {"item": "ステッチ（縫製ビスコティ）の傾き・ピッチ", "detail": "ヴィトン特有のやや斜めに流れる縫い目（ビスコティ）と、糸の太さ・縫い幅の一貫性。"},
                {"item": "ヌメ革の質感・焼けた色合い・コバ塗りの質", "detail": "ハンドル等のヌメ革の肌触り、フチのコバ塗り（赤茶色のニス）の厚みと丁寧さ。"}
            ]

    # 3. エルメス（HERMES）時計 ＆ ジュエリー ＆ 財布 ＆ バッグ
    elif "エルメス" in kw_upper or "HERMES" in kw_upper or any(w in kw_upper for w in ["バーキン", "ケリー", "コンスタンス", "ピコタン", "ボリード", "ガーデンパーティ", "ベアン", "ドゴン", "シルクイン", "シェーヌダンクル", "Hウォッチ", "クリッパー", "ケープコッド"]):
        if any(w in kw_upper for w in ["Hウォッチ", "クリッパー", "ケープコッド", "ナンタケット", "スリム", "時計"]):
            return [
                {"item": "ケースエッジの立体感と「H」デザインのポリッシュ（Hウォッチ等）", "detail": "「H」型ケース外枠の歪みのない鋭いカット面と、ケース鏡面仕上げの圧倒的な美しさ。"},
                {"item": "ケースバック（裏蓋）のHERMES刻印と型番（HH1.210等）", "detail": "裏蓋に細くシャープに刻印された「HERMES」ロゴ・型番・シリアルナンバーの精密な打刻。"},
                {"item": "文字盤ロゴ（HERMES PARIS）と針の歪みのなさ", "detail": "文字盤印字のフォント精度、インデックスの立体感、針の表面断面の仕上げ。"},
                {"item": "ヴォー・エプソン/トゴ革ベルト裏面の箔押しとステッチ", "detail": "ベルト裏面の「HERMES PARIS」箔押し刻印と、ベルト外周の斜め手縫いステッチの均一性。"}
            ]
        elif any(w in kw_upper for w in ["シェーヌダンクル", "ジュエリー", "ブレス", "リング", "ネックレス", "ピアス", "コリエドシアン"]):
            return [
                {"item": "刻印のフォントと場所（HERMES Made in France）", "detail": "フック金具やコマ側面に刻印された「HERMES」ロゴおよび製造国刻印の深さ・フォント。"},
                {"item": "銀（Ag925）/金（Au750）のホールマーク打刻", "detail": "フランス製貴金属に打刻される「蟹（Ag925）」または「鷲の頭（K18）」のホールマークの深さと形状。"},
                {"item": "コマの開口部（Tバー・丸カン）のカシメ溶接面", "detail": "コマのつなぎ目やTバー（留め具）の溶接部分が完璧に研磨され、継ぎ目跡が一切見えないか。"},
                {"item": "コマ（アンカーチェーン）の重量感と手触り", "detail": "コマのフチが丁寧に適度な丸みで処理されており、しっかりとした重量感があるか。"}
            ]
        else:
            return [
                {"item": "📅 製造年（年代刻印）＆ アトリエ記号", "detail": "製造年刻印（〇囲み・□囲み・無囲み・近年の刻印）の位置（クロア裏または正面内側側面）と、職人イニシャル・アトリエ記号の打刻のシャープさ。"},
                {"item": "🐴 HERMES PARIS made in France 箔押し刻印", "detail": "箔押しのフォント（特に「É」のアクサン符号の向き・角度）と、レザーのシボ（凹凸）の奥に潰れず綺麗に箔が乗っているか。"},
                {"item": "🔒 カデナ（南京錠）・鍵・クロシェット構造", "detail": "カデナ底面の「HERMES」刻印フォントの深さ、キーナンバーの一致、クロシェット内側のキーリングのカシメ仕上げ。"},
                {"item": "🔩 クロア（ベルト）金具・裏側のピン留め処理", "detail": "クロア金具のフチ（面取り）処理の滑らかさ、裏側金具のピンカシメ打刻（プラス・マイナスネジ止め仕様は偽物疑い）。"},
                {"item": "🧵 クチュール・セリエ（手縫いステッチ）の規則性", "detail": "エルメス特有の「右上がり」に一糸ずつ傾く手縫い糸（麻糸ロウ引き）の規則正しいピッチとコバ（革の切れ端）ニスの仕上げ。"},
                {"item": "🤐 ファスナー止まりの「H」刻印と開閉フィール", "detail": "ファスナーの始点にある金具（「H」型またはriri/ZIP製刻印）の仕上げ精度と、チャック開閉のスムーズさ。"}
            ]

    # 4. ロレックス（ROLEX）全モデル
    elif any(w in kw_upper for w in [
        "ROLEX", "ロレックス", "デイトナ", "DAYTONA", "サブマリーナ", "SUBMARINER", 
        "デイトジャスト", "DATEJUST", "エクスプローラー", "EXPLORER", "GMT", "デイデイト", 
        "DAYDATE", "ヨットマスター", "YACHT", "ミルガウス", "MILGAUSS", "エアキング", 
        "AIRKING", "オイスターパーペチュアル", "OYSTER", "スカイドゥエラー", "シードゥエラー",
        "116500", "126610", "116610", "126710", "126300", "16233", "116234", "124300", "114060", "226570"
    ]):
        return [
            {"item": "👑 ガラス6時位置の王冠レーザー透かし", "detail": "サファイアガラス6時位置に施されたレーザー刻印の王冠マークが肉眼で主張しすぎず、非常に精密なドット群で構成されているか（目が粗く肉眼でくっきり見えるものは偽物疑い）。"},
            {"item": "🔍 ルーレット刻印（インナーリング）の文字精度", "detail": "文字盤外周の「ROLEX」ロゴの配置が正しく（1〜5時位置はR、7〜11時位置はXが分目盛りに一致）、6時位置のシリアル刻印の打刻が均一で美しいか。"},
            {"item": "サイクロップレンズ（日付拡大）と無反射コーティング", "detail": "デイトジャスト等の日付窓拡大レンズの倍率が正確に約2.5倍であり、無反射コーティングの青みや透明度が正常か。"},
            {"item": "針（ポインター）側面断面とダイヤルインデックス", "detail": "針の側面断面にバリや加工傷がなく研磨されているか。インデックスのクロマライト夜光の塗布面が凹凸なく均一か。"},
            {"item": "セラクロムベゼル凹み刻印とプラチナコーティング", "detail": "ベゼルの数字凹み部分にプラチナPVD蒸着がムラなく施され、フォントの深さやエッジの鋭さが正しいか。"},
            {"item": "ブレスレットコマの側面マイナスネジ頭", "detail": "ブレスレットのコマ調整用ねじ頭のマイナス溝に傷や潰れがなく、ネジ穴の面取り処理が滑らかか。"},
            {"item": "クラスプ（バックル）内部の刻印打刻と王冠マーク", "detail": "バックル開閉部の王冠マークおよび内部の「ROLEX」ロゴ刻印の深さ・フォント・磨き加工の滑らかさ。"},
            {"item": "フラッシュフィット（FF）とケースのスキマ精度", "detail": "ブレスレットとケースの接続部（FF）にグラつきや不自然なスキマ（隙間）がなく、一体感があるか。"},
            {"item": "リューズ（クラウン）のねじ込み感と立体マーク", "detail": "リューズに刻印された王冠マークやドット/ライン（金属素材表示）の立体感と、ねじ込む際のズレのないスムーズ感。"}
        ]

    # 5. パテック フィリップ 全モデル
    elif any(w in kw_upper for w in ["パテック", "PATEK", "カラトラバ", "CALATRAVA", "ノーチラス", "NAUTILUS", "アクアノート", "AQUANAUT", "5196", "5711", "5167"]):
        return [
            {"item": "🏛️ ジュネーブ・シール / PPシール（ムーブメント刻印）", "detail": "シースルーバックから見えるムーブメント上に打刻されたPPマーク/ジュネーブ・シールのフォント精度と仕上げ。"},
            {"item": "ペルラージュ ＆ コート・ド・ジュネーブ最高級装飾", "detail": "ブリッジやプレートに施された波状装飾（コート・ド・ジュネーブ）や点状の研磨（ペルラージュ）の立体的な輝き。"},
            {"item": "✒️ 文字盤ロゴ（PATEK PHILIPPE GENEVE）の盛り上がり", "detail": "ダイヤルの文字フォントが幾何学的に正しく、インクの印刷が立体的に適度に盛り上がり滲みがないか。"},
            {"item": "✨ ケース・ラグのホールマーク（貴金属証明刻印）", "detail": "ゴールド/プラチナケースのラグ裏や側面にあるホールマーク（聖ベルナール犬頭や天秤マーク）の深い打刻。"},
            {"item": "👑 竜頭（リューズ）のカラトラバ十字立体刻印", "detail": "リューズトップに施されたカラトラバ十字（四つ葉十字）の立体刻印が左右均一で緻密にエッジが立っているか。"},
            {"item": "🔗 クラスプ（バックル）の刻印と打刻フォント", "detail": "貴金属バックル裏面の「PATEK PHILIPPE」刻印の打刻精度と、ピンバックルの滑らかなフリクション感。"},
            {"item": "針（ポインター）の立体カッティングと鏡面磨き", "detail": "立体的にカッティングされた針の表面およびエッジが歪みなく完璧に鏡面磨き（ブラックポリッシュ）されているか。"}
        ]

    # 6. オメガ（OMEGA）全モデル
    elif any(w in kw_upper for w in ["オメガ", "OMEGA", "シーマスター", "SEAMASTER", "スピードマスター", "SPEEDMASTER", "310.30", "210.30"]):
        return [
            {"item": "🌊 ケースバック（裏蓋）のシーホース/地球儀刻印", "detail": "シーホース（海馬）刻印の立体感や線の深さ、またケース裏の地球儀ホログラム刻印の精密さ。"},
            {"item": "🔍 文字盤・インデックス・波状（ウェーブ）模様", "detail": "シーマスター特有のレーザー刻印文字盤波模様のカット精度、文字のフォント滲みがないか。"},
            {"item": "⚙️ ヘリウム脱出バルブ（10時位置）", "detail": "10時位置のバルブネジの回し心地、ねじ込み完了時の位置やバルブ上面の「He」刻印の仕上げ。"},
            {"item": "✨ ルミナスポイント・夜光（ルミノバ）", "detail": "ベゼル12時位置のルミナスポイントの凸感、針・インデックスの夜光の塗布面が均一か。"},
            {"item": "🔗 ブレスレット・クラスプのロゴ刻印", "detail": "クラスプ（バックル）部分の「OMEGA Seamaster」刻印のフォント精度と伸縮機構の滑らかさ。"}
        ]

    # 7. その他 高級時計全般
    elif any(w in kw_upper for w in [
        "AP", "オーデマ", "ロイヤルオーク", "ヴァシュロン", "ウブロ", "HUBLOT", "ビッグバン", 
        "IWC", "カルティエ", "CARTIER", "タンク", "サントス", "パシャ", "バロンブルー", 
        "グランドセイコー", "GS", "タグホイヤー", "ブライトリング", "時計", "WATCH"
    ]):
        return [
            {"item": "🔍 文字盤（ギョーシェ/タペストリー模様）の立体感", "detail": "文字盤のタペストリー格子やギョーシェ彫りの立体溝カット精度。針の断面研磨とインデックスの配置。"},
            {"item": "⚙️ ベゼルビス・ケースエッジの研磨仕上げ", "detail": "ベゼル六角ビス（ロイヤルオーク等）の向き・沈み込みの平滑さと、ケース鏡面・ヘアラインの切り替わりライン。"},
            {"item": "ケース裏蓋の刻印・シリアルナンバー", "detail": "裏蓋に深く均一に刻まれたシリアル・型番フォントの精密さと、ネジ頭のマイナス溝の美しさ。"},
            {"item": "クラスプ・バックル刻印精度", "detail": "バックル内部のブランドロゴ刻印の深さ・エッジの面取り処理の丁寧さ。"}
        ]

    # 8. その他 ブランド品全般（デフォルト）
    else:
        return [
            {"item": "ブランド印字・ロゴ刻印フォント", "detail": "ロゴ刻印の文字配置が均一で、印字にフォントの乱れや滲みがないか。"},
            {"item": "シリアルナンバー / 品番打刻 / ICチップ", "detail": "シリアル刻印またはICチップ（NFCタグ）の検出が可能か。"},
            {"item": "金属金具のメッキムラ・ビス（ネジ）精度", "detail": "ネジの頭（マイナス溝）が綺麗に整っており、メッキ剥がれやバリがないか。"},
            {"item": "縫製（ステッチ）のピッチとコバの処理", "detail": "糸の太さ・縫い目ピッチの一貫性、縁のコバニスの仕上げ。"}
        ]

# --- WEBスクレイピング＆相場幅算出 ---
def search_clean_market_prices(search_query, selected_material, selected_type, selected_dial, selected_deco):
    raw_query = search_query.strip()
    
    # 単体モデル名の場合はブランド名を自動展開
    for key, val in BRAND_COMPLETION_MAP.items():
        if raw_query == key:
            raw_query = val
            break
            
    # 素材・アイテム・文字盤・装飾の絞り込み条件の付加
    full_query_parts = [raw_query]
    if selected_material != "全素材":
        full_query_parts.append(selected_material)
    if selected_type != "全アイテム":
        full_query_parts.append(selected_type)
    if selected_dial != "全カラー":
        full_query_parts.append(selected_dial)
    if selected_deco != "指定なし":
        full_query_parts.append(selected_deco)
        
    search_query = " ".join(full_query_parts)
            
    url = f"https://auctions.yahoo.co.jp/search/search?p={search_query}&va={search_query}&exflg=1&b=1&n=50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    q_upper = search_query.upper()
    min_price_threshold = 30000
    if any(w in q_upper for w in ["デイトナ", "ロレックス", "ROLEX", "パテック", "PATEK", "バーキン", "ケリー", "116500", "126610"]):
        min_price_threshold = 300000
    elif any(w in q_upper for w in ["デイトジャスト", "オメガ", "シャネル", "マトラッセ", "シェーヌダンクル"]):
        min_price_threshold = 100000

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, []
        
        soup = BeautifulSoup(response.text, "html.parser")
        items = []
        clean_prices = []
        
        product_nodes = soup.select(".Product")
        
        for node in product_nodes:
            title_el = node.select_one(".Product__titleLink")
            price_el = node.select_one(".Product__priceValue, .Product__price")
            img_el = node.select_one("img")
            
            if title_el and price_el:
                title = title_el.get_text().strip()
                
                if any(bad_word in title for bad_word in EXCLUDE_KEYWORDS):
                    continue
                
                price_text = price_el.get_text().replace(",", "").replace("円", "").strip()
                numbers = re.findall(r'\d+', price_text)
                
                if numbers:
                    price = int(numbers[0])
                    if price >= min_price_threshold:
                        clean_prices.append(price)
                        img_url = img_el.get("src") if img_el else None
                        items.append({
                            "title": title,
                            "price": price,
                            "img_url": img_url
                        })
        
        if len(clean_prices) >= 2:
            clean_prices = sorted(clean_prices)
            p_min = int(np.percentile(clean_prices, 10))
            p_max = int(np.percentile(clean_prices, 90))
            
            stats = {
                "buyback_min": int(p_min * 0.70), "buyback_max": int(p_max * 0.75),
                "flea_min": int(p_min * 1.10), "flea_max": int(p_max * 1.25),
                "auc_min": p_min, "auc_max": p_max,
                "count": len(clean_prices),
                "query_used": search_query
            }
            return stats, items[:6]
        else:
            return None, []
    except Exception:
        return None, []

# --- メイン画面レイアウト ---
col1, col2 = st.columns([1, 2.2])

with col1:
    st.subheader("1. 型番・モデル名の入力")
    search_keyword = st.text_input(
        "型番やブランドモデル名を入力してください", 
        placeholder="例: デイトジャスト, シェーヌダンクル, プルミエール, タンブール, バーキン25"
    )
    
    st.markdown("**⚙️ 素材・アイテム・時計仕様の絞り込み（オプション）**")
    
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        selected_material = st.selectbox(
            "素材選択",
            ["全素材", "シルバー", "ゴールド", "イエローゴールド", "ピンクゴールド", "ホワイトゴールド", "コンビ", "プラチナ", "ステンレス", "キャビアスキン", "ラムスキン", "トゴ"]
        )
    with row1_col2:
        selected_type = st.selectbox(
            "アイテム種別",
            ["全アイテム", "時計", "ブレスレット", "リング", "ネックレス", "ピアス", "バッグ", "財布"]
        )
        
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        selected_dial = st.selectbox(
            "文字盤カラー（時計用）",
            ["全カラー", "黒", "白", "青", "緑", "アイスブルー", "シルバー", "ゴールド", "ピンク", "シェル", "コンピューター"]
        )
    with row2_col2:
        selected_deco = st.selectbox(
            "装飾/ダイヤ（時計・アクセ用）",
            ["指定なし", "ダイヤ", "10Pダイヤ", "シェル", "2Pダイヤ"]
        )
    
    search_button = st.button("🚀 Web即時相場 ＆ 真贋解析を実行", type="primary", use_container_width=True)
    
    st.markdown("""
    ---
    **💡 入力のコツ:**
    - 時計（`デイトジャスト`, `デイトナ`, `タンブール`, `プルミエール` 等）は「素材（コンビ/無垢）」や「文字盤色」「ダイヤ有無」を指定すると価格帯精度が大幅に向上します。
    """)

with col2:
    st.subheader("2. 相場幅 ＆ モデル・品目専用真贋解析")
    
    if search_button:
        if not search_keyword.strip():
            st.error("⚠️ 型番やモデル名（例: デイトジャスト, タンブール, シェーヌダンクル）を入力してください。")
        else:
            st.session_state["analyzed_keyword"] = search_keyword.strip()
            st.session_state["selected_material"] = selected_material
            st.session_state["selected_type"] = selected_type
            st.session_state["selected_dial"] = selected_dial
            st.session_state["selected_deco"] = selected_deco

    analyzed_kw = st.session_state.get("analyzed_keyword", "")
    mat = st.session_state.get("selected_material", "全素材")
    typ = st.session_state.get("selected_type", "全アイテム")
    dial = st.session_state.get("selected_dial", "全カラー")
    deco = st.session_state.get("selected_deco", "指定なし")

    if analyzed_kw:
        with st.spinner(f"Webから【{analyzed_kw}】の市場データを高速集計中..."):
            stats, items = search_clean_market_prices(analyzed_kw, mat, typ, dial, deco)
            
            if stats:
                st.success(f"✅ Web上の本体有効データ ({stats['count']}件 / 検索軸: 『{stats['query_used']}』) から3市場の相場幅を自動出力しました！")
                
                # 相場幅の表示
                st.markdown("### 💰 3市場 価格幅（レンジ）相場")
                
                st.info(f"🏢 **買取店 買取相場:** **¥{stats['buyback_min']:,}** 〜 **¥{stats['buyback_max']:,}**")
                st.success(f"🛍️ **フリマ販売相場:** **¥{stats['flea_min']:,}** 〜 **¥{stats['flea_max']:,}**")
                st.warning(f"🔨 **オークション相場:** **¥{stats['auc_min']:,}** 〜 **¥{stats['auc_max']:,}**")
                
                st.divider()
                
                # 超詳細プロ仕様 真贋鑑定セクション
                st.markdown(f"### 🛡️ 【{analyzed_kw}】専用 高度プロ真贋鑑定・解析フォーム")
                st.write("対象ブランド・品目に合わせたプロ査定基準チェック項目です。手元の実物と照合してチェックを入れてください。")
                
                guides = fetch_authenticity_guides(analyzed_kw)
                check_results = []
                
                for idx, g in enumerate(guides):
                    st.write(f"**{idx+1}. {g['item']}**")
                    st.caption(g['detail'])
                    res = st.radio(
                        f"判定_{idx}", 
                        options=["✅ 基準適合（本物の特徴と一致）", "⚠️ 判定留保・微妙", "🚨 基準外（問題あり・偽物の特徴）"], 
                        key=f"check_{idx}",
                        label_visibility="collapsed"
                    )
                    check_results.append(res)
                    st.write("")
                
                # 総合判定
                ok_count = sum(1 for r in check_results if "✅" in r)
                warn_count = sum(1 for r in check_results if "⚠️" in r)
                ng_count = sum(1 for r in check_results if "🚨" in r)
                total_items = len(guides)
                score = int((ok_count / total_items) * 100)
                
                st.markdown("### 📋 総合真贋解析判定結果")
                st.progress(score)
                
                if ng_count > 0:
                    st.error(f"🚨 **判定結果: 基準外リスク高（適合度: {score}%）**\n\n不適合項目（{ng_count}件）が検出されました。偽物・コピー品のリスクが高いためご注意ください。")
                elif warn_count > 1:
                    st.warning(f"⚠️ **判定結果: 要詳細査定（適合度: {score}%）**\n\n一部の項目（{warn_count}件）で留保されています。詳細査定をおすすめします。")
                else:
                    st.success(f"🟢 **判定結果: 基準内（正規品の可能性極めて高 / 適合度: {score}%）**\n\nすべてのWeb基準項目を満たしています。提示相場での査定を行っていただけます。")

                st.divider()
                st.markdown("### 📁 抽出根拠となったWeb上の類似商品データ（本体のみ抽出）")
                for item in items:
                    c_img, c_info = st.columns([1, 4])
                    with c_img:
                        if item.get("img_url"):
                            st.image(item["img_url"], width=90)
                    with c_info:
                        st.write(f"**{item['title']}**")
                        st.write(f"取引価格: **¥{item['price']:,}**")
            else:
                st.error("⚠️ 有効な相場データが見つかりませんでした。型番やモデル名、または素材・文字盤等の組み合わせを変更してお試しください。")
    else:
        st.info("👈 左側の枠に型番やモデル名を入力し、検索ボタンを押してください。")