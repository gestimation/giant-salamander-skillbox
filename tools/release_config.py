"""Single source of truth for public plugin release metadata."""

from __future__ import annotations

from copy import deepcopy


REPOSITORY_URL = "https://github.com/gestimation/giant-salamander-skillbox"
RELEASE_REF = "skillbox-2026.08.16"
AUTHOR = {
    "name": "gestimation",
    "url": REPOSITORY_URL,
}

BUNDLE_NAME = "giant-salamander-skillbox"
BUNDLE_VERSION = "1.0.0"
BUNDLE_FILENAME = f"{BUNDLE_NAME}-{BUNDLE_VERSION}.zip"
BUNDLE_DESCRIPTION = (
    "Review tables and citations, plan study size, and draft medical costs."
)
BUNDLE_KEYWORDS = [
    "statistics",
    "tables",
    "citations",
    "sample-size",
    "medical-costs",
    "research",
]
BUNDLE_INTERFACE = {
    "displayName": "Giant Salamander Skillbox",
    "shortDescription": "Tables, citations, size & cost",
    "longDescription": (
        "Giant Salamander Skillbox combines readatable for reconstructing statistical "
        "tables, reviewcitation for checking citations and public bibliographic records "
        "when host web access is available, and samplesize200 for validated sample-size, "
        "event, power, and detectable-effect calculations. It also includes "
        "draftcostsheet for traceable medical-cost sheets using authoritative unit-cost "
        "sources when host web access is available. No separate gestimation account or "
        "authentication is required, and user content is not sent to a "
        "gestimation-operated server."
    ),
    "developerName": "gestimation",
    "category": "Productivity",
    "capabilities": ["Interactive"],
    "websiteURL": REPOSITORY_URL,
    "privacyPolicyURL": f"{REPOSITORY_URL}/blob/main/docs/PRIVACY.md",
    "termsOfServiceURL": f"{REPOSITORY_URL}/blob/main/docs/TERMS.md",
    "defaultPrompt": [
        "Use readatable to reconstruct this statistical table while preserving headers, units, sample sizes, and footnotes.",
        "Use reviewcitation to reconcile in-text citations with the reference list and flag items needing verification.",
        "Use samplesize200 for study size or draftcostsheet for a source-linked medical-cost sheet.",
    ],
}

PUBLISHED_ASSET_SHA256 = {
    "readatable-0.7.1.zip": (
        "cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a"
    ),
    "reviewcitation-0.3.4.zip": (
        "8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad"
    ),
    "samplesize200-1.0.0-rc.8.zip": (
        "88643f5c1635ae2371cbfd3db5a381fa6593a1540bf6360d1f53abc02091a1f5"
    ),
    "samplesize200-1.0.0-rc.9.zip": (
        "971aa1f7234019df167266e2630344a759905192c11b394da34e07a461544cf5"
    ),
    "draftcostsheet-0.2.2.zip": (
        "cfbcedb66cb6a398a8ebe5c3dafe9b9fedb22dfbac35ae0f57a9d51c9410fdbc"
    ),
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
        "version": "1.0.0-rc.9",
        "filename": "samplesize200-1.0.0-rc.9.zip",
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
    "draftcostsheet": {
        "version": "0.2.2",
        "filename": "draftcostsheet-0.2.2.zip",
        "description": "Draft traceable medical-cost sheets from authoritative sources.",
        "keywords": ["medical-costs", "costing", "health-economics", "research"],
        "interface": {
            "displayName": "draftcostsheet",
            "shortDescription": "医療費を出典付きで再現・試算します。",
            "longDescription": "治療、プロトコール、診療経路または既存の費用推計から、資源量と単価を分離した追跡可能な医療費シートを作成します。対象地域、価格時点、価格概念、時間範囲を明示し、利用可能な場合は公的な単価資料を取得します。根拠が不足する場合は値を推測せず、部分推計または未解決として報告します。",
            "developerName": "gestimation",
            "category": "Productivity",
            "capabilities": ["Interactive"],
            "defaultPrompt": "この治療の患者1人あたり医療費を公的な単価資料から見積もって",
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


def codex_bundle_manifest() -> dict[str, object]:
    return {
        "name": BUNDLE_NAME,
        "version": BUNDLE_VERSION,
        "description": BUNDLE_DESCRIPTION,
        "author": deepcopy(AUTHOR),
        "homepage": REPOSITORY_URL,
        "repository": REPOSITORY_URL,
        "license": "MIT",
        "keywords": list(BUNDLE_KEYWORDS),
        "skills": "./skills/",
        "interface": deepcopy(BUNDLE_INTERFACE),
    }


def claude_bundle_manifest() -> dict[str, object]:
    return {
        "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
        "name": BUNDLE_NAME,
        "displayName": BUNDLE_INTERFACE["displayName"],
        "version": BUNDLE_VERSION,
        "description": BUNDLE_DESCRIPTION,
        "author": deepcopy(AUTHOR),
        "homepage": REPOSITORY_URL,
        "repository": REPOSITORY_URL,
        "license": "MIT",
        "keywords": list(BUNDLE_KEYWORDS),
        "skills": "./skills/",
    }


def codex_marketplace() -> dict[str, object]:
    return {
        "name": BUNDLE_NAME,
        "interface": {"displayName": BUNDLE_INTERFACE["displayName"]},
        "plugins": [
            {
                "name": BUNDLE_NAME,
                "source": {
                    "source": "git-subdir",
                    "url": f"{REPOSITORY_URL}.git",
                    "path": f"./plugins/{BUNDLE_NAME}",
                    "ref": RELEASE_REF,
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        ],
    }


def claude_marketplace() -> dict[str, object]:
    return {
        "name": BUNDLE_NAME,
        "owner": deepcopy(AUTHOR),
        "description": BUNDLE_DESCRIPTION,
        "plugins": [
            {
                "name": BUNDLE_NAME,
                "displayName": BUNDLE_INTERFACE["displayName"],
                "source": {
                    "source": "git-subdir",
                    "url": f"{REPOSITORY_URL}.git",
                    "path": f"plugins/{BUNDLE_NAME}",
                    "ref": RELEASE_REF,
                },
                "description": BUNDLE_DESCRIPTION,
                "version": BUNDLE_VERSION,
                "author": deepcopy(AUTHOR),
                "homepage": REPOSITORY_URL,
                "repository": REPOSITORY_URL,
                "license": "MIT",
                "keywords": list(BUNDLE_KEYWORDS),
                "category": "Research",
            }
        ],
    }
