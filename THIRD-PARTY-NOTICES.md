# Third-party material

The original skill instructions and scripts are MIT licensed; see LICENSE.

`assets/public_suffix_list.dat` is an unmodified source-form snapshot of the Public Suffix List, distributed under Mozilla Public License 2.0. Its original notices are preserved. The license text is included as `assets/MPL-2.0.txt` and is also available at https://mozilla.org/MPL/2.0/.

- Official source: https://publicsuffix.org/list/public_suffix_list.dat
- Format and update guidance: https://publicsuffix.org/list/
- Snapshot header VERSION: 2026-10-07_07-28-19_UTC
- Snapshot header COMMIT: 3929462652695bad04f0a27afb600974014a3c8b
- SHA256: ba7d836c0ea57a8bcf9f1fcb868066a7554bed029b441ecc6204ad8494a32612

The list is used offline to reject public suffixes, including private hosting suffixes, as rule scope. It does not prove a domain belongs to a particular service. Future maintainers should update it from the official source, preserve notices, run tests and update this provenance before releasing. No automatic updater or background download is installed.
