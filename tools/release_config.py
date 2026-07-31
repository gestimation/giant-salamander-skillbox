"""Single source of truth for public plugin release metadata."""

from __future__ import annotations

from copy import deepcopy


REPOSITORY_URL = "https://github.com/gestimation/giant-salamander-skillbox"
AUTHOR = {
    "name": "gestimation",
    "url": REPOSITORY_URL,
}

PLUGINS = {
    "readatable": {
        "version": "0.7.1",
        "filename": "readatable-0.7.1.zip",
        "description": "Reconstruct and normalize complex statistical tables.",
        "keywords": ["tables", "statistics", "data-extraction"],
        "interface": {
            "displayName": "readatable",
            "shortDescription": "複雑な統計表を読みやすく再構成します。",
            "longDescription": "統計表の階層、変数、統計量、単位、注記、出典を保ちながら、読みやすい表や構造化データへ整理します。",
            "developerName": "gestimation",
            "category": "Productivity",
            "capabilities": ["Interactive"],
            "defaultPrompt": "この表を読みやすく整理して",
        },
    },
    "reviewcitation": {
        "version": "0.3.4",
        "filename": "reviewcitation-0.3.4.zip",
        "description": "Review scientific citations and reference lists for integrity.",
        "keywords": ["citations", "references", "scientific-writing"],
        "interface": {
            "displayName": "reviewcitation",
            "shortDescription": "科学文書の引用と参考文献を点検します。",
            "longDescription": "本文中の引用と参考文献一覧を照合し、番号、書誌情報、引用の配置、根拠との対応をレビューします。",
            "developerName": "gestimation",
            "category": "Productivity",
            "capabilities": ["Interactive"],
            "defaultPrompt": "この文書の引用文献をレビューして",
        },
    },
    "samplesize200": {
        "version": "1.0.0-rc.6",
        "filename": "samplesize200-1.0.0-rc.6.zip",
        "description": "Plan and calculate study size with 188 validated calculators.",
        "keywords": ["sample-size", "power", "statistics", "study-design"],
        "interface": {
            "displayName": "samplesize200",
            "shortDescription": "研究デザインに応じたサンプルサイズを設計します。",
            "longDescription": "188の検証済み計算方法と105の研究例を使い、必要サンプルサイズ、必要イベント数、達成検出力などを対話形式で計画します。",
            "developerName": "gestimation",
            "category": "Productivity",
            "capabilities": ["Interactive"],
            "defaultPrompt": "この研究に必要なサンプルサイズを計算して",
        },
    },
}


def plugin_manifest(name: str) -> dict[str, object]:
    config = PLUGINS[name]
    return {
        "name": name,
        "version": config["version"],
        "description": config["description"],
        "author": deepcopy(AUTHOR),
        "homepage": REPOSITORY_URL,
        "repository": REPOSITORY_URL,
        "license": "MIT",
        "keywords": list(config["keywords"]),
        "skills": "./skills/",
        "interface": deepcopy(config["interface"]),
    }
