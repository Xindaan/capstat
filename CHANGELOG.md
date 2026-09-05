# Changelog

## [0.3.1](https://github.com/Xindaan/capstat/compare/v0.3.0...v0.3.1) (2026-09-05)


### Documentation

* **task,state:** record the 0.3.0 publish, and correct two things ([9c65a9b](https://github.com/Xindaan/capstat/commit/9c65a9b1a7d7440fe4e51149d8187e572441d571))
* **task,state:** record the 0.3.0 release and the notes it nearly shipped ([fb0c952](https://github.com/Xindaan/capstat/commit/fb0c95289dfd7deabebc040be99400d7bed6c49e))

## [0.3.0](https://github.com/Xindaan/capstat/compare/v0.2.1...v0.3.0) (2026-09-05)


### ⚠ BREAKING CHANGES

* **core,api,web:** every warning carries a code (T-0074). A warning crosses
  the HTTP contract as `{code, message}` rather than a bare string, and
  `capstat-core`'s `warnings` tuples hold `Caveat` rather than `str`.
  `Caveat` is a `str` subclass, so printing, joining and `"text" in warning`
  are unaffected; a client reading `warnings` as JSON strings is not.
  ([e3abe9f](https://github.com/Xindaan/capstat/commit/e3abe9f9dadadd9e00a1f61e8eb5581905324aeb))


### Features

* **core,api,web:** every warning carries a code (T-0074) ([e3abe9f](https://github.com/Xindaan/capstat/commit/e3abe9f9dadadd9e00a1f61e8eb5581905324aeb))
* **api:** a local CLI over the same parser and the same core (T-0077) ([05fc732](https://github.com/Xindaan/capstat/commit/05fc732d223c2ca602747f138a8dff52626c28bf))
* **api:** cap the compute request body at 10 MB (T-0063) ([d1473ad](https://github.com/Xindaan/capstat/commit/d1473ad257a79702ca21f46212641fbe17336977))
* **core,api,web:** judge new data against a known baseline (T-0076) ([9129626](https://github.com/Xindaan/capstat/commit/9129626798664e2d84c2034f6e57a24f3aaac842))
* **web:** judge Cp/Cpk against a stated requirement (T-0073) ([5f66ab0](https://github.com/Xindaan/capstat/commit/5f66ab0a0de2d17342745a199d6b56a2dc35abbc))
* **web:** reach the subgrouped analyses from the page (T-0075) ([6d12d64](https://github.com/Xindaan/capstat/commit/6d12d646e864fa8603fa62030b0cc411d44cc6f1))


### Bug fixes

* **api:** read a German Excel CSV, and name what was detected (T-0067) ([a090433](https://github.com/Xindaan/capstat/commit/a09043300b0359365394233a81f6fafd03015d0c))
* **core:** carry the inner report's warnings through the Box-Cox path (T-0064) ([2d52a4d](https://github.com/Xindaan/capstat/commit/2d52a4d048cde3a5d2dcdfcd51bdb8cc46dff325))
* **core:** let no absolute tolerance hide a lopsided chart (T-0069) ([3ce24e7](https://github.com/Xindaan/capstat/commit/3ce24e733bf25621f7d721a8e34b2865e8e22f1f))
* **core:** name the pooled ceiling's quantity, and say what went untested ([e62e990](https://github.com/Xindaan/capstat/commit/e62e990ad7c247bca164d35c26d0a6c53c8e60ca))
* **core:** reject a lot claiming acceptance at a tighter AQL (T-0066) ([c704704](https://github.com/Xindaan/capstat/commit/c70470421e6518de2dbfec7056a25bf79549f865))
* **e2e:** wait on the request, not on a poll budget (T-0049) ([5c2fafe](https://github.com/Xindaan/capstat/commit/5c2fafea086217988f676db263e7b6fee70060e2))
* **screenshots:** drop a reload flag that was doing nothing ([0b7626c](https://github.com/Xindaan/capstat/commit/0b7626ceba0bc514bb33b6677d386a22720174bd))
* **web:** stop a two-digit dimension eating the Gage R&R grid (T-0065) ([32ccd4e](https://github.com/Xindaan/capstat/commit/32ccd4eec733e20cdf9e03fc131b17e1dfb3ff36))


### Documentation

* close the drift between the steering files and the code (T-0072) ([f9f9103](https://github.com/Xindaan/capstat/commit/f9f91032530638b2af8c5ef75d5571250242f37d))
* **images:** re-shoot the README figures against the current UI (T-0079) ([dd415c2](https://github.com/Xindaan/capstat/commit/dd415c226ee269843cb7219e78b7309f542abbe8))
* **state:** correct the commit count on the branch ([95b92fb](https://github.com/Xindaan/capstat/commit/95b92fb2c5d849a7d330d416fc16c43c1d352d2c))
* **task:** park the Next-generated agent files, with the tripwire named (T-0050) ([0a23634](https://github.com/Xindaan/capstat/commit/0a23634e8f455b9fd052b322b5a11b8f977bf511))
* **task:** record the dependency sweep, and what merging on a stale tick cost ([bdf66d9](https://github.com/Xindaan/capstat/commit/bdf66d9ae92272e14d3226cf83cc929dbb973e8f))


### Refactoring

* **web:** key the analyses on a counter, not a fingerprint (T-0071) ([16d4e20](https://github.com/Xindaan/capstat/commit/16d4e206162b0d7187552f135aae92a22c958fd3))

## [0.2.1](https://github.com/Xindaan/capstat/compare/v0.2.0...v0.2.1) (2026-08-16)


### Bug fixes

* **ci:** publish a tag, not whatever main happens to hold (T-0045) ([eb31d4f](https://github.com/Xindaan/capstat/commit/eb31d4fd952eb39d063eea179386abc35916d8bb))
* **lint:** keep ruff 0.16 out of the Markdown, and main green again ([63c0051](https://github.com/Xindaan/capstat/commit/63c005133b3788fc59a9027275b30b04733a17fa))
* **web:** clear the last two advisories, and the audit brace-expansion (T-0046) ([fe579ba](https://github.com/Xindaan/capstat/commit/fe579ba5ac9080d61dfff2f936fbfeba724c727a))


### Documentation

* record the PyPI publication, and fix what it made stale ([77e1036](https://github.com/Xindaan/capstat/commit/77e1036850da44aa6ac5aeedc8d1f804a110cc8f))
* **task:** capture T-0046 -- the npm advisories outgrew T-0023's framing ([45eff03](https://github.com/Xindaan/capstat/commit/45eff03b1f8dd19f84395fc5034cb6121d7b03bf))

## [0.2.0](https://github.com/Xindaan/capstat/compare/v0.1.0...v0.2.0) (2026-07-27)


### Features

* **api,web:** acceptance sampling end to end (T-0037) ([73588ed](https://github.com/Xindaan/capstat/commit/73588ede19b0e06c7c484c3b592e066fb61a4cb9))
* **api,web:** the switching scheme reaches the app (T-0036, increment 2b) ([b4dd6cc](https://github.com/Xindaan/capstat/commit/b4dd6cc421edb84249d8c6172765313941af2c03))
* **community:** enable Discussions so the question link resolves (T-0043) ([3ed373f](https://github.com/Xindaan/capstat/commit/3ed373fa4a352aca8f8204f0910fa443dce8a38e))
* **core:** acceptance sampling, computed rather than looked up (T-0035) ([5a5402d](https://github.com/Xindaan/capstat/commit/5a5402dc61c950bbb85a585f98b28c5ae8dde468))
* **core:** complete the ISO 2859-1 switching scheme, and fix a rule I had wrong ([ef9daae](https://github.com/Xindaan/capstat/commit/ef9daae02cc843ad9956b40e3aa98de1d22a5b2e))
* **core:** ISO 2859-1 switching rules, the half we can stand behind (T-0036) ([1c5c673](https://github.com/Xindaan/capstat/commit/1c5c673949ae5d5a42a07ecd030b8daca1eb3ecf))
* **sampling:** report ISO 2859-1's limiting quality (T-0036, increment 1) ([b37e987](https://github.com/Xindaan/capstat/commit/b37e987f3c341d12c45d29d3158fd76b41899482))
* **web:** choose which run rules apply; clear the dependency backlog ([ff17086](https://github.com/Xindaan/capstat/commit/ff170866e4732b7cc140011e594d12f6cdb74f5d))
* **web:** finish the study file, and stop the e2e suite racing the dev server ([9979da3](https://github.com/Xindaan/capstat/commit/9979da3bf9d026ce5b88af7c443f002eb54e7ab6))
* **web:** save and reload a study as a file you own (T-0041, partly) ([676da13](https://github.com/Xindaan/capstat/commit/676da13db0f8d0c801b44340ba8f6b7416deacf4))


### Bug fixes

* **security:** enable private vulnerability reporting (T-0044) ([c921f54](https://github.com/Xindaan/capstat/commit/c921f54644759adce9ac274ab3b2376daf67b7a0))


### Documentation

* **sampling:** name the bring-your-own-plan path; fix a racing e2e assertion ([e9b103b](https://github.com/Xindaan/capstat/commit/e9b103b5f20f8a10d2430fc5451e65984cb49f69))
* show the app, with numbers the library actually computed (T-0031) ([7a920aa](https://github.com/Xindaan/capstat/commit/7a920aaf6314c3504dadeb89eee0e7a4b34387b6))
* **state:** record the public flip, and capture what it exposed ([20d4ecc](https://github.com/Xindaan/capstat/commit/20d4eccbb7bd4a31641751af8944741269205c2b))
* **task:** capture T-0044 (SECURITY.md names a reporting channel the repo has disabled) ([737c289](https://github.com/Xindaan/capstat/commit/737c2898b6c56cd0471d8b3cc974ad42eb7ae2f4))
* **task:** T-0030 -- record the publish reasoning; visibility gate cleared ([40d0fca](https://github.com/Xindaan/capstat/commit/40d0fcad622e70378d630abd7adb4e464714a1a1))

## 0.1.0 (2026-07-21)


### Features

* **api:** /compute/{bias,linearity,stability} + typed client (T-0025a) ([7088fa5](https://github.com/Xindaan/capstat/commit/7088fa5ebc2ee4f7e00b0429da274a479f74aa21))
* **api:** /compute/gage-rr endpoint (both methods) + typed client ([5580690](https://github.com/Xindaan/capstat/commit/55806902581d292c6c8a42f28253ccde3b8e66ff))
* **api:** FastAPI service wrapping capstat-core with a faithful OpenAPI contract ([b8ef526](https://github.com/Xindaan/capstat/commit/b8ef52600a511b9d2c2da44d3a9e5cfb6b805124))
* **core:** bias study — is the gage right, not just consistent (T-0013a) ([8a1c24d](https://github.com/Xindaan/capstat/commit/8a1c24d06d516f24f52df7b80348b83cceb1dd77))
* **core:** capability indices with the two sigmas kept apart ([24349c4](https://github.com/Xindaan/capstat/commit/24349c4168de7f8307f4ec12dcae8badd2b9f6b0))
* **core:** control-chart constants and Shewhart charts ([b4f55c5](https://github.com/Xindaan/capstat/commit/b4f55c508251e846162e98167404aa7f94ec65ca))
* **core:** descriptive and robust statistics, NIST StRD validated ([261d803](https://github.com/Xindaan/capstat/commit/261d8036306bb70dd569a4cd01eda4f07c7a4d43))
* **core:** EWMA and CUSUM, the charts that see what Shewhart misses ([5ec3985](https://github.com/Xindaan/capstat/commit/5ec398550301be160a38e412664de960a28b8cdb))
* **core:** gage linearity — does the bias drift across the range (T-0013b) ([11c4a95](https://github.com/Xindaan/capstat/commit/11c4a95886038a33b841b72b21ec2a351d31ef1c))
* **core:** Gage R&R by ANOVA — the gage's share of the variation ([627514a](https://github.com/Xindaan/capstat/commit/627514a5751b634a70822e462db06c2f4cc5701d))
* **core:** Gage R&R by average-and-range, with a computed d2* ([f48298a](https://github.com/Xindaan/capstat/commit/f48298a652a66fe161e90e31d35dd8b149b04a60))
* **core:** Nelson and Western Electric run rules ([1e7a302](https://github.com/Xindaan/capstat/commit/1e7a302890554a752fd2735383d241107760ecf1))
* **core:** normality tests with an honest verdict ([634cdc7](https://github.com/Xindaan/capstat/commit/634cdc71e8bafed6f603e259a01b5c27f868dd48))
* **core:** stability — a control chart on a master part (T-0013c) ([0b12c83](https://github.com/Xindaan/capstat/commit/0b12c8308e4cc2215a808ee3fd0092dee8266e3e))
* **deploy:** Dockerfiles, compose and a deployment guide (T-0015a) ([99e8c00](https://github.com/Xindaan/capstat/commit/99e8c004c42d8ec183478446a7fdbfe3bddfc944))
* **web:** /msa page — bias, linearity and stability (T-0025b) ([fb86de7](https://github.com/Xindaan/capstat/commit/fb86de7d31e9850bd0c0593278a3c090d0339d10))
* **web:** capability dashboard — the decision path, made visible ([23b40d5](https://github.com/Xindaan/capstat/commit/23b40d51f44fee88672f75db7bdd87fb9b76fb8c))
* **web:** every analysis page is its own report (T-0014) ([eb95d32](https://github.com/Xindaan/capstat/commit/eb95d327e612430c9685f62634d5989bd4574330))
* **web:** Gage R&R page — a data-entry grid to a variance verdict ([18ed688](https://github.com/Xindaan/capstat/commit/18ed68859c146a29d95f72109678475d55db7c20))
* **web:** I-MR control charts with a Nelson run-rule overlay ([7c8bdd3](https://github.com/Xindaan/capstat/commit/7c8bdd3171b76d8545f54a8c53ee95b29c170362))
* **web:** typed API client + Next.js scaffold ([6afdd76](https://github.com/Xindaan/capstat/commit/6afdd76110d5aa39ebebf62f69fb6b9e46896a1d))
* **web:** upload flow — ingest a file, pick a column, see the warnings ([ec3e1ac](https://github.com/Xindaan/capstat/commit/ec3e1ac33a7ed82afd615649d0b825db5c20bd38))


### Bug fixes

* **api:** the schema check compares contracts, not bytes (T-0034) ([32640ff](https://github.com/Xindaan/capstat/commit/32640ff4bf26af0ee3707d24da949fe8a1e9df4c))
* **core:** a degenerate Box-Cox no longer crashes the capability path ([e0ffa19](https://github.com/Xindaan/capstat/commit/e0ffa1963e96991cfdde55a0fdcb36a378626b54))
* **core:** type the bias test helper explicitly for numpy's 3.11 stubs ([0516866](https://github.com/Xindaan/capstat/commit/051686632d2ae23545f1a485d58c9ec796a1b089))
* **deploy:** the web image copied a public/ directory that does not exist ([68250e5](https://github.com/Xindaan/capstat/commit/68250e50156cd50feb3cffadfeff967fdf7a4fe9))
* **web:** an absent index says why, instead of a bare dash (T-0028) ([06110f1](https://github.com/Xindaan/capstat/commit/06110f1c1ee4da0a0f5276cffb005240ca858ffc))
* **web:** the row index is no longer analysed as a measurement (T-0033) ([7807d95](https://github.com/Xindaan/capstat/commit/7807d958faf6cc997f89aa9c9282f3f3ea75713c))


### Performance

* **constants:** 75x faster d3 by keeping scipy out of the integrand ([c1f24ee](https://github.com/Xindaan/capstat/commit/c1f24ee49bde2f8175065b04a640d7cfd1408871))


### Documentation

* correct the demo-CSV numbers — I quoted the wrong function ([928db24](https://github.com/Xindaan/capstat/commit/928db2485e7e9734daf8a15f6171b5273f209c16))
* correct why a release PR shows no checks (T-0017b) ([3b9008c](https://github.com/Xindaan/capstat/commit/3b9008c13ab5713c4ce4ea01146dc7d18066bcff))
* mkdocs-material site with a generated sources page (T-0016) ([6924160](https://github.com/Xindaan/capstat/commit/69241605e5a977ad73cc5d1d90227ecdf52834c5))
* record the local-only hosting decision; correct a release misdiagnosis ([89d00ab](https://github.com/Xindaan/capstat/commit/89d00ab647367a7e288fb148a6167f9c662c3fae))
* **task:** capture T-0020 (CI actions on deprecated Node 20 runtime) ([f5ddc0f](https://github.com/Xindaan/capstat/commit/f5ddc0f7616458dd324cca53e793bf059317cd8c))


### Tests

* **web:** unit + e2e safety net for the front end (T-0011 M4 done) ([ed2fe9a](https://github.com/Xindaan/capstat/commit/ed2fe9a74031a15af8cec9d70e0b5e82f0654a81))
