# Changelog

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
