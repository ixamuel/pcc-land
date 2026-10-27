# Bundled PDF dependencies

The distribution files are embedded as scripts in `index.html`. No CDN, runtime fetch, package install, or server is needed by the user. Source-map directives are removed; license headers are retained.

| Package | Version | Source file SHA-256 |
| --- | --- | --- |
| jspdf | 4.2.1 | `e6551fcdc32f09d6853b2c5126d18d01d9447e0da618a41a11ebeee0f6c20d54` |
| svg2pdf.js | 2.8.1 | `2f10c0d16959e9a0c4cfd8605cfce0830ddc384337f74fa0351a6eff1c1efb8b` |

Official documentation: [jsPDF](https://github.com/parallax/jsPDF), [svg2pdf.js](https://github.com/yWorks/svg2pdf.js). Both use the MIT license; copies are in this directory.

## Updating

1. Download pinned packages with npm into a temporary directory, with lifecycle scripts disabled. The current versions are `jspdf@4.2.1` and `svg2pdf.js@2.8.1`.
2. Replace the corresponding embedded UMD scripts, leaving their license headers intact. Remove `sourceMappingURL` comments and escape any literal closing script tags for safe HTML embedding. Do not change the generated catalog or application markers.
3. Update this version/checksum record and licenses.
4. Run `node tests/dimensions.test.cjs`, then verify a generated PDF in a browser. Check A4 page size, vector paths, both patterns, all annotations, title/table/footer, and grid inclusion.

The application uses only jsPDF document creation and svg2pdf vector conversion. Optional HTML rendering dependencies are not invoked.
