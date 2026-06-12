# Changelog

## [1.7.0](https://github.com/landonia/claude-plugins/compare/pm-v1.6.2...pm-v1.7.0) (2026-06-12)


### Features

* **pm:** add --auto flag and /pm:autoplan orchestrator ([b728e9a](https://github.com/landonia/claude-plugins/commit/b728e9a228209d060d78099d4c85a9c7dd18a1c6))
* **pm:** add --auto override flag to authoring commands ([2680d03](https://github.com/landonia/claude-plugins/commit/2680d03c75d7c871e6dc2e399437ac86ed777c5b))
* **pm:** add /pm:autoplan authoring-pipeline orchestrator ([f7cbfa2](https://github.com/landonia/claude-plugins/commit/f7cbfa26527d9e3ff142cdd350bf618da5433a7a))
* **pm:** add opt-in --parallel flag to /pm:auto ([#15](https://github.com/landonia/claude-plugins/issues/15)) ([f8c8a1e](https://github.com/landonia/claude-plugins/commit/f8c8a1ebe2ed8d096851027e51eda33c4e747c8f))

## [1.6.2](https://github.com/landonia/claude-plugins/compare/pm-v1.6.1...pm-v1.6.2) (2026-06-10)


### Bug Fixes

* **pm:** make /pm:auto snapshot deterministic and fix in-progress resume ([e6f0bcb](https://github.com/landonia/claude-plugins/commit/e6f0bcbfdcd543eecf77a1a4d9e3f3a5dcb22715))

## [1.6.1](https://github.com/landonia/claude-plugins/compare/pm-v1.6.0...pm-v1.6.1) (2026-06-09)


### Bug Fixes

* **pm:** parse args when /pm:auto orchestrator passes it as a JSON string ([6591ead](https://github.com/landonia/claude-plugins/commit/6591ead1b33aeeb897231fea6d4135d0b91ab5b4))

## [1.6.0](https://github.com/landonia/claude-plugins/compare/pm-v1.5.2...pm-v1.6.0) (2026-06-09)


### Features

* **pm:** log resolved max-retries at /pm:auto startup ([31d7c64](https://github.com/landonia/claude-plugins/commit/31d7c648f063b907d7fe103bb0270817fb0df104))


### Bug Fixes

* **pm:** harden slug recovery in /pm:auto workflow ([695d894](https://github.com/landonia/claude-plugins/commit/695d894517c870d49e7edc90e16b125d722899ee))

## [1.5.2](https://github.com/landonia/claude-plugins/compare/pm-v1.5.1...pm-v1.5.2) (2026-06-09)


### Bug Fixes

* **pm:** parse --max-retries deterministically in /pm:auto workflow ([e3a2c18](https://github.com/landonia/claude-plugins/commit/e3a2c18b1c41fd8bf25e1f30d7c5ed57fb4ac006))
* **pm:** recover slug from tasksDir in /pm:auto workflow prompts ([1174963](https://github.com/landonia/claude-plugins/commit/1174963c2a09094b3c67f96360884af8ac68852c))

## [1.5.1](https://github.com/landonia/claude-plugins/compare/pm-v1.5.0...pm-v1.5.1) (2026-06-08)


### Bug Fixes

* **pm:** make /pm:auto loop deterministic to stop premature stalls ([62fc8d9](https://github.com/landonia/claude-plugins/commit/62fc8d9bde3a00b977047c3467face27153feb91))

## [1.5.0](https://github.com/landonia/claude-plugins/compare/pm-v1.4.0...pm-v1.5.0) (2026-06-08)


### Features

* **pm:** add task complexity score and /pm:gantt chart ([#6](https://github.com/landonia/claude-plugins/issues/6)) ([e16e92a](https://github.com/landonia/claude-plugins/commit/e16e92a60b786f6ed51945c10edda7903307dcf1))

## [1.4.0](https://github.com/landonia/claude-plugins/compare/pm-v1.3.0...pm-v1.4.0) (2026-06-07)


### Features

* **pm:** add /pm:auto autonomous execute→verify loop ([9818ca5](https://github.com/landonia/claude-plugins/commit/9818ca5044e7b2badcfa0203ae00d13a8d1e8e6d))

## [1.3.0](https://github.com/landonia/claude-plugins/compare/pm-v1.2.0...pm-v1.3.0) (2026-06-07)


### Features

* **pm:** add /pm:test test-strategy command and testing.md artifact ([96f7237](https://github.com/landonia/claude-plugins/commit/96f7237af6592b195f243bc0bbfb775ec4c2edd8))
* **pm:** parallel subagent dispatch in /pm:execute ([96c15e6](https://github.com/landonia/claude-plugins/commit/96c15e65281eb57a33202d1c25eec2d0438a41bd))

## [1.2.0](https://github.com/landonia/claude-plugins/compare/pm-v1.1.0...pm-v1.2.0) (2026-06-05)


### Features

* **pm:** add /pm:express fast-path planning command ([9a5e3fd](https://github.com/landonia/claude-plugins/commit/9a5e3fdb048ffd30237c2d589331a1a9221ba0dc))

## [1.1.0](https://github.com/landonia/claude-plugins/compare/pm-v1.0.0...pm-v1.1.0) (2026-06-05)


### Features

* **pm:** add /pm:handoff command for mid-task context passing ([0d1007b](https://github.com/landonia/claude-plugins/commit/0d1007bc8ad6550900fba8bb2b5f7a903db079f5))

## Changelog
