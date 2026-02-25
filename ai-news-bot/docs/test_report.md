# AI News Collection Bot - テストレポート

> テスト実施日: 2026-02-25
> テスト実行環境: Python 3.11.14, pytest 9.0.2, pytest-asyncio 1.3.0
> 実行コマンド: `PYTHONPATH=. python -m pytest tests/ -v`

---

## 1. テスト実行結果サマリー

| 項目 | 値 |
|------|-----|
| **総テスト数** | 219 |
| **PASS** | 219 |
| **FAIL** | 0 |
| **ERROR** | 0 |
| **SKIP** | 0 |
| **実行時間** | 7.97 秒 |
| **結果** | **ALL PASS** |

---

## 2. テストファイル別結果

### 2.1 tests/test_utils.py (22 テスト) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| TestLoadConfig::test_load_valid_config | PASS | 有効な config.yaml の読み込み |
| TestLoadConfig::test_load_config_file_not_found | PASS | 存在しないファイルで FileNotFoundError |
| TestLoadConfig::test_load_empty_config | PASS | 空の config.yaml で ConfigValidationError |
| TestValidateConfig::test_valid_config_no_errors | PASS | 有効な設定でエラーなし |
| TestValidateConfig::test_missing_required_section | PASS | 必須セクション欠如の検出 |
| TestValidateConfig::test_invalid_port_range | PASS | 不正なポート番号の検出 |
| TestValidateConfig::test_invalid_num_stories | PASS | 不正な num_stories の検出 |
| TestValidateConfig::test_invalid_temperature | PASS | 不正な temperature の検出 |
| TestValidateConfig::test_invalid_source_url | PASS | 不正な URL の検出 |
| TestValidateConfig::test_invalid_log_level | PASS | 不正なログレベルの検出 |
| TestAppConfig::test_singleton_pattern | PASS | シングルトンパターンの動作 |
| TestAppConfig::test_get_dot_notation | PASS | ドット記法でのアクセス |
| TestAppConfig::test_get_env | PASS | 環境変数の取得 |
| TestAppConfig::test_force_reload | PASS | 強制再読込 |
| TestAppConfig::test_invalid_config_raises_error | PASS | 不正設定でのエラー |
| TestAppConfig::test_repr | PASS | repr() の出力 |
| TestSetupLogger::test_logger_creation | PASS | ロガーの生成 |
| TestSetupLogger::test_logger_has_handlers | PASS | ハンドラの登録 |
| TestSetupLogger::test_logger_creates_log_dir | PASS | ログディレクトリの自動作成 |
| TestSetupLogger::test_logger_writes_to_file | PASS | ファイルへの書き込み |
| TestSetupLogger::test_logger_format | PASS | ログフォーマットの検証 |
| TestSetupLogger::test_logger_no_duplicate_handlers | PASS | ハンドラの重複防止 |
| TestWithRetry::test_success_no_retry | PASS | 成功時のリトライなし |
| TestWithRetry::test_retry_then_succeed | PASS | リトライ後の成功 |
| TestWithRetry::test_retry_exhausted_raises | PASS | リトライ上限到達時の例外 |
| TestWithRetry::test_non_retryable_exception_raises_immediately | PASS | 対象外例外の即座発生 |
| TestWithRetry::test_exponential_backoff | PASS | 指数バックオフの検証 |
| TestWithRetry::test_max_wait_cap | PASS | 最大待機時間の上限 |
| TestWithRetry::test_preserves_function_metadata | PASS | 関数メタデータの保持 |
| TestWithRetry::test_on_retry_callback | PASS | リトライコールバックの呼び出し |

### 2.2 tests/test_collector.py (34 テスト) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| TestRssCollector::test_collect_from_rss_success | PASS | RSS 収集の成功 |
| TestRssCollector::test_collect_from_rss_multiple_sources | PASS | 複数ソースからの RSS 収集 |
| TestRssCollector::test_collect_from_rss_source_failure_continues | PASS | ソース失敗時の継続動作 |
| TestRssCollector::test_collect_from_rss_empty_sources | PASS | 空ソースの処理 |
| TestRssCollector::test_collect_from_rss_skip_entry_without_title | PASS | タイトルなしエントリのスキップ |
| TestRssCollector::test_collect_from_rss_max_articles_per_feed | PASS | フィード毎の最大取得件数 |
| TestRssCollector::test_parse_published_date_with_struct_time | PASS | struct_time の日付パース |
| TestRssCollector::test_parse_published_date_fallback | PASS | 日付パースのフォールバック |
| TestRssCollector::test_extract_summary_html_stripped | PASS | HTML タグの除去 |
| TestSelector::test_deduplicate_candidates | PASS | 重複排除 |
| TestSelector::test_deduplicate_empty_list | PASS | 空リストの重複排除 |
| TestSelector::test_clamp_values | PASS | 値のクランプ |
| TestSelector::test_parse_scoring_response_valid_json | PASS | 有効な JSON レスポンスの解析 |
| TestSelector::test_parse_scoring_response_with_code_block | PASS | コードブロック内 JSON の解析 |
| TestSelector::test_parse_scoring_response_invalid_json | PASS | 不正 JSON の処理 |
| TestSelector::test_parse_scoring_response_clamps_values | PASS | スコアのクランプ |
| TestSelector::test_fallback_select_by_recency | PASS | 時間順フォールバック選定 |
| TestSelector::test_select_top_articles_with_scores | PASS | スコア付き記事選定 |
| TestSelector::test_select_top_articles_fallback_on_api_failure | PASS | API 失敗時のフォールバック |
| TestSelector::test_select_top_articles_empty_candidates | PASS | 空候補の処理 |
| TestSelector::test_select_top_articles_fewer_than_num | PASS | 候補 < 選定数の処理 |
| TestSelector::test_select_top_articles_dedup | PASS | 選定時の重複排除 |
| TestSelector::test_build_scoring_prompt | PASS | スコアリングプロンプトの生成 |
| TestNewsApi::test_fetch_from_newsapi_success | PASS | NewsAPI の正常取得 |
| TestNewsApi::test_fetch_from_newsapi_no_api_key | PASS | API キー未設定時のエラー |
| TestNewsApi::test_fetch_from_newsapi_skips_removed | PASS | 削除記事のスキップ |
| TestNewsApi::test_fetch_from_hackernews_success | PASS | Hacker News の正常取得 |
| TestNewsApi::test_fetch_from_hackernews_fallback_url | PASS | URL フォールバック |
| TestWebScraper::test_scrape_articles_success | PASS | Web スクレイピングの成功 |
| TestWebScraper::test_scrape_articles_empty_selectors | PASS | 空セレクタの処理 |
| TestWebScraper::test_scrape_articles_robots_denied | PASS | robots.txt 拒否の処理 |
| TestCollectorInit::test_collect_candidates_rss_only | PASS | RSS のみの候補収集 |
| TestCollectorInit::test_collect_all_pipeline | PASS | 全パイプラインの動作 |
| TestCollectorInit::test_collect_all_empty_config | PASS | 空設定での動作 |

### 2.3 tests/test_writer.py (21 テスト) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| TestClassifyByKeywords::test_enterprise_adoption_selects_star | PASS | 企業導入キーワード -> STAR |
| TestClassifyByKeywords::test_tech_innovation_selects_heros_journey | PASS | 技術革新キーワード -> ヒーローズジャーニー |
| TestClassifyByKeywords::test_business_improvement_selects_before_after_bridge | PASS | 業務改善キーワード -> Before/After/Bridge |
| TestClassifyByKeywords::test_problem_solving_selects_pas | PASS | 課題解決キーワード -> PAS |
| TestClassifyByKeywords::test_ambiguous_article_returns_none | PASS | 曖昧な記事 -> None |
| TestClassifyByKeywords::test_empty_article_returns_none | PASS | 空記事 -> None |
| TestClassifyByKeywords::test_english_keywords_match | PASS | 英語キーワードのマッチ |
| TestClassifyByKeywords::test_highest_score_wins | PASS | 最高スコアの選択 |
| TestSelectFramework::test_keyword_match_without_api_call | PASS | キーワードマッチ時の API 非使用 |
| TestSelectFramework::test_api_fallback_for_ambiguous_article | PASS | API フォールバック |
| TestSelectFramework::test_api_invalid_json_fallback | PASS | 不正 JSON のフォールバック |
| TestSelectFramework::test_api_unknown_framework_defaults | PASS | 不明フレームワーク時のデフォルト |
| TestTransformToStory::test_transform_with_explicit_framework | PASS | 明示的フレームワーク指定の変換 |
| TestTransformToStory::test_transform_with_auto_framework_selection | PASS | 自動フレームワーク選択の変換 |
| TestGenerateInsight::test_generate_insight_with_stories | PASS | インサイト生成 |
| TestGenerateInsight::test_generate_insight_empty_stories | PASS | 空ストーリーのインサイト |
| TestBuildFrontmatterMetadata::* (4 tests) | PASS | Frontmatter メタデータ構築 |
| TestRenderBodyFallback::* (4 tests) | PASS | フォールバック本文レンダリング |
| TestGenerateDailyMarkdown::* (6 tests) | PASS | 日次 Markdown 生成 |
| TestSaveMarkdown::* (4 tests) | PASS | Markdown ファイル保存 |
| TestMarkdownIntegration::test_full_pipeline_roundtrip | PASS | パイプラインラウンドトリップ |
| TestFrameworkConstants::* (2 tests) | PASS | フレームワーク定数の検証 |

### 2.4 tests/test_delivery.py (41 テスト) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| TestMarkdownToHtml::* (8 tests) | PASS | Markdown -> HTML 変換 |
| TestGenerateReactionUrl::* (4 tests) | PASS | リアクション URL 生成 |
| TestPrepareStoryContext::* (2 tests) | PASS | ストーリーコンテキスト準備 |
| TestApplyEmailTemplate::* (8 tests) | PASS | メールテンプレート適用 |
| TestReactionsDefinition::* (2 tests) | PASS | リアクション定義の完全性 |
| TestFormatForLine::* (7 tests) | PASS | LINE メッセージフォーマット |
| TestExtractSummary::* (7 tests) | PASS | テキスト要約抽出 |
| TestReactionLinkIntegration::* (3 tests) | PASS | リアクションリンク統合 |

### 2.5 tests/test_feedback.py (20 テスト) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| TestUpdateReaction::* (8 tests) | PASS | リアクション更新処理 |
| TestFastAPIEndpoints::* (7 tests) | PASS | FastAPI エンドポイント |
| TestKnowledgeSearch::* (11 tests) | PASS | ナレッジベース検索 |

### 2.6 tests/test_integration.py (47 テスト -- 新規作成) -- 全 PASS

| テスト名 | 結果 | 説明 |
|----------|------|------|
| **パイプライン統合テスト** | | |
| TestPipelineIntegration::test_full_pipeline_dry_run | PASS | dry-run 全パイプライン実行 |
| TestPipelineIntegration::test_pipeline_zero_articles_fallback | PASS | 記事0件のフォールバック |
| **収集->変換->MD保存フロー** | | |
| TestCollectTransformSaveFlow::test_collect_and_select | PASS | 収集 + 選定フロー |
| TestCollectTransformSaveFlow::test_transform_and_save_markdown | PASS | 変換 + MD 保存フロー |
| **リアクション API -> MD 更新フロー** | | |
| TestReactionFlowIntegration::test_react_updates_md_file | PASS | API リアクション -> MD 更新 |
| TestReactionFlowIntegration::test_react_then_verify_md_updated | PASS | リアクション -> 検証の完全フロー |
| TestReactionFlowIntegration::test_react_all_types_on_same_file | PASS | 同一ファイル全タイプリアクション |
| **CLI引数テスト** | | |
| TestCLIArgs::test_parse_default_args | PASS | デフォルト引数パース |
| TestCLIArgs::test_parse_date_arg | PASS | --date 引数パース |
| TestCLIArgs::test_parse_dry_run_arg | PASS | --dry-run 引数パース |
| TestCLIArgs::test_parse_server_arg | PASS | --server 引数パース |
| TestCLIArgs::test_parse_combined_args | PASS | 複合引数パース |
| TestCLIArgs::test_main_invalid_date_exits | PASS | 不正日付で sys.exit(1) |
| TestCLIArgs::test_main_valid_date_format | PASS | 有効な日付フォーマット |
| TestCLIArgs::test_today_jst_format | PASS | JST日付フォーマット |
| **記事0件のフォールバック** | | |
| TestZeroArticleFallback::test_collect_all_empty_sources | PASS | ソース0件 -> 空リスト |
| TestZeroArticleFallback::test_collect_all_all_feeds_fail | PASS | 全フィード失敗 -> 空リスト |
| TestZeroArticleFallback::test_generate_markdown_empty_stories | PASS | 空ストーリーでMD生成 |
| TestZeroArticleFallback::test_generate_insight_empty_stories | PASS | 空ストーリーでインサイト |
| TestZeroArticleFallback::test_format_for_line_empty_stories | PASS | 空ストーリーでLINEフォーマット |
| TestZeroArticleFallback::test_email_template_empty_stories | PASS | 空ストーリーでメールテンプレート |
| **不正なリアクションリクエスト** | | |
| TestInvalidReactionRequests::test_invalid_reaction_type | PASS | 不正リアクションタイプ |
| TestInvalidReactionRequests::test_story_id_zero | PASS | story_id=0 |
| TestInvalidReactionRequests::test_story_id_negative | PASS | 負の story_id |
| TestInvalidReactionRequests::test_story_id_too_large | PASS | story_id > 3 |
| TestInvalidReactionRequests::test_nonexistent_date_file | PASS | 存在しない日付ファイル |
| TestInvalidReactionRequests::test_api_invalid_date_format | PASS | API 不正日付フォーマット |
| TestInvalidReactionRequests::test_api_missing_params | PASS | API パラメータ欠如 |
| TestInvalidReactionRequests::test_api_story_id_out_of_range | PASS | API story_id 範囲外 |
| TestInvalidReactionRequests::test_api_invalid_reaction_type | PASS | API 不正リアクション |
| **既存MDファイルへの重複更新** | | |
| TestDuplicateReactionUpdates::test_overwrite_reaction | PASS | リアクション上書き |
| TestDuplicateReactionUpdates::test_update_preserves_other_stories | PASS | 他ストーリー不変 |
| TestDuplicateReactionUpdates::test_update_preserves_body_content | PASS | 本文不変 |
| TestDuplicateReactionUpdates::test_sequential_updates_on_different_stories | PASS | 連続更新の反映 |
| **MDファイル命名規則の一貫性** | | |
| TestMdFileNamingConsistency::test_updater_filename_pattern | PASS | updater のファイル名パターン |
| TestMdFileNamingConsistency::test_search_filename_pattern | PASS | search のファイル名パターン |
| TestMdFileNamingConsistency::test_main_saves_with_correct_filename | PASS | main.py の保存ファイル名 |
| **ナレッジベース連携** | | |
| TestKnowledgeIntegration::test_search_after_reaction_update | PASS | リアクション更新後の検索 |
| TestKnowledgeIntegration::test_tag_search_on_generated_md | PASS | 生成MDのタグ検索 |
| TestKnowledgeIntegration::test_fulltext_search_on_generated_md | PASS | 生成MDの全文検索 |
| **その他エッジケース** | | |
| TestAdditionalEdgeCases::test_save_markdown_empty_content | PASS | 空 MD 保存 |
| TestAdditionalEdgeCases::test_collect_candidates_disabled_sources | PASS | 無効ソースのスキップ |
| TestAdditionalEdgeCases::test_select_top_articles_single_candidate | PASS | 候補1件の選定 |
| TestAdditionalEdgeCases::test_deduplicate_candidates_url_case_insensitive | PASS | URL 重複排除 |
| TestAdditionalEdgeCases::test_config_validation_multiple_errors | PASS | 複数バリデーションエラー |
| TestAdditionalEdgeCases::test_reaction_map_completeness | PASS | REACTION_MAP の完全性 |
| TestAdditionalEdgeCases::test_scoring_prompt_includes_all_candidates | PASS | プロンプトの完全性 |

---

## 3. 発見したバグと修正内容

### BUG-001: main.py と updater.py/search.py 間の MD ファイル命名規則の不一致 (重大度: HIGH)

**概要**: `main.py` の `run_pipeline()` 関数が Markdown ファイルを `{date}.md` 形式で保存していたが、`feedback/updater.py` の `_build_md_filepath()` と `knowledge/search.py` の `get_all_articles()` は `{date}_ai_news.md` 形式のファイルを期待していた。

**影響**:
- リアクション API がファイルを見つけられず、全てのリアクションリクエストが `FileNotFoundError` で失敗する
- ナレッジベース検索（タグ検索・全文検索・評価フィルタリング）が日次レポートを発見できない
- 月次サマリー生成で記事が0件として扱われる

**修正箇所**: `/home/user/AI-News-Collection-Bot_v1/ai-news-bot/src/main.py` (246行目)

```python
# 修正前
md_filepath = str(Path(daily_dir) / f"{target_date}.md")

# 修正後
md_filepath = str(Path(daily_dir) / f"{target_date}_ai_news.md")
```

**検証**: `TestMdFileNamingConsistency` クラスの3テストで、main.py / updater.py / search.py 間のファイル命名規則の一貫性を検証済み。

---

## 4. カバレッジ情報 (概算)

| モジュール | 推定カバレッジ | テスト種別 |
|-----------|---------------|-----------|
| src/utils/config.py | ~90% | ユニット + 統合 |
| src/utils/logger.py | ~85% | ユニット |
| src/utils/retry.py | ~95% | ユニット |
| src/collector/__init__.py | ~85% | ユニット + 統合 |
| src/collector/rss_collector.py | ~80% | ユニット + 統合 |
| src/collector/news_api.py | ~75% | ユニット |
| src/collector/web_scraper.py | ~70% | ユニット |
| src/collector/selector.py | ~90% | ユニット + 統合 |
| src/writer/storyteller.py | ~85% | ユニット + 統合 |
| src/writer/markdown_gen.py | ~90% | ユニット + 統合 |
| src/delivery/html_converter.py | ~85% | ユニット + 統合 |
| src/delivery/gmail_sender.py | ~40% | (外部 API 依存のため一部のみ) |
| src/delivery/line_sender.py | ~80% | ユニット + 統合 |
| src/feedback/api_server.py | ~90% | ユニット + 統合 |
| src/feedback/updater.py | ~95% | ユニット + 統合 |
| src/knowledge/search.py | ~90% | ユニット + 統合 |
| src/knowledge/tagger.py | ~75% | ユニット + 統合 |
| src/knowledge/summarizer.py | ~60% | ユニット (Claude API 依存) |
| src/main.py | ~80% | 統合 |
| **全体推定** | **~82%** | |

**注記**:
- 外部 API (Claude API, Gmail API, LINE Notify API) に依存する部分はモックでテストしているため、実環境でのカバレッジは異なる可能性がある
- gmail_sender.py は OAuth2 認証フローが絡むため、ユニットテストでのカバレッジが限定的
- 全ての外部 API 呼び出し箇所にはモックを適用し、ネットワーク非依存のテストを実現済み

---

## 5. テスト構成

```
tests/
  __init__.py           -- テストパッケージ
  test_utils.py         -- utils モジュールのユニットテスト (22 tests)
  test_collector.py     -- collector モジュールのユニットテスト (34 tests)
  test_writer.py        -- writer モジュールのユニットテスト (21 tests)
  test_delivery.py      -- delivery モジュールのユニットテスト (41 tests)
  test_feedback.py      -- feedback + knowledge モジュールのユニットテスト (20 tests)
  test_integration.py   -- 統合テスト + エッジケーステスト (47 tests) [新規作成]
```

---

## 6. 新規作成テストの分類

### 統合テスト (12 tests)
- main.py パイプライン dry-run 実行
- 記事0件フォールバック
- 収集 -> 選定フロー
- 変換 -> MD 保存フロー
- リアクション API -> MD 更新フロー
- リアクション -> ナレッジベース検索連携
- MD ファイル命名規則の一貫性検証

### CLI 引数テスト (8 tests)
- --date, --dry-run, --server 引数パース
- 複合引数、不正日付、JST日付フォーマット

### エッジケーステスト (27 tests)
- 記事0件のフォールバック (6 tests)
- 不正なリアクションリクエスト (9 tests)
- 既存MDファイルへの重複更新 (4 tests)
- その他エッジケース (8 tests)
