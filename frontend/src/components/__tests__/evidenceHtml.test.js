import { evidenceDetailsHtml } from "../poeRegistry";

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const t = (k) => ({ poeEvidenceTitle: "Official source" })[k] ?? k;

describe("evidenceDetailsHtml", () => {
  const html = evidenceDetailsHtml(
    { url: "https://www.gov.bm/visitors", domain: "gov.bm", snippet: "ships clear at the Port of Hamilton, a port of entry.", entry_term: "port of entry" },
    { name: "Port of Hamilton" }, t, esc,
  );

  test("the link sits beside the disclosure, never inside its summary", () => {
    const summary = html.match(/<summary>([\s\S]*?)<\/summary>/)[1];
    expect(summary).not.toContain("<a ");
    expect(summary).toContain("Official source: gov.bm");
    expect(html).toContain('<a class="m-link" href="https://www.gov.bm/visitors"');
  });

  test("the excerpt is marked and the link is labelled", () => {
    expect(html).toContain('<mark class="m-mark">Port of Hamilton</mark>');
    expect(html).toContain('<mark class="m-mark">port of entry</mark>');
    expect(html).toContain('aria-label="Official source: gov.bm"');
  });
});
