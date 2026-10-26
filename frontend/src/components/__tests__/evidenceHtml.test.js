import { evidenceDetailsHtml } from "../poeRegistry";
import { installDisclosureToggles } from "../../lib/a11y";

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const t = (k) => ({ poeEvidenceTitle: "Official source" })[k] ?? k;

describe("evidenceDetailsHtml", () => {
  const html = evidenceDetailsHtml(
    { url: "https://www.gov.bm/visitors", domain: "gov.bm", snippet: "ships clear at the Port of Hamilton, a port of entry.", entry_term: "port of entry" },
    { name: "Port of Hamilton" }, t, esc,
  );

  test("the domain is shown once, as the link, beside the toggle (never inside it)", () => {
    const toggle = html.match(/<button[^>]*data-disclosure[^>]*>([\s\S]*?)<\/button>/)[1];
    expect(toggle).not.toContain("<a ");
    expect(toggle).not.toContain("gov.bm");
    expect(toggle).toContain("Official source:");
    expect(html).toContain('<a class="m-link" href="https://www.gov.bm/visitors"');
    const visible = html.replace(/<[^>]+>/g, " ");
    expect(visible.match(/gov\.bm/g)).toHaveLength(1);
  });

  test("the excerpt is marked and starts hidden", () => {
    expect(html).toContain('<mark class="m-mark">Port of Hamilton</mark>');
    expect(html).toContain('<mark class="m-mark">port of entry</mark>');
    expect(html).toMatch(/data-disclosure-body hidden/);
  });

  test("the delegated toggle opens and closes the excerpt", () => {
    const off = installDisclosureToggles(document);
    document.body.innerHTML = html;
    const btn = document.querySelector("[data-disclosure]");
    const body = document.querySelector("[data-disclosure-body]");
    btn.click();
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(body.hidden).toBe(false);
    btn.click();
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(body.hidden).toBe(true);
    off();
    document.body.innerHTML = "";
  });
});
