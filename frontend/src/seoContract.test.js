import { readFileSync, existsSync } from "fs";
import { join } from "path";

const publicDir = join(__dirname, "..", "public");

describe("contrat SEO blueintelligence.online", () => {
  it("index.html : lang fr, marque, canonical, JSON-LD", () => {
    const html = readFileSync(join(publicDir, "index.html"), "utf8");
    expect(html).toMatch(/<html lang="fr"/);
    expect(html).toMatch(/Blue Intelligence by Berry-Mappemonde/);
    expect(html).toMatch(/rel="canonical" href="https:\/\/www\.blueintelligence\.online\/"/);
    expect(html).toMatch(
      /name="google-site-verification" content="5QUxdIp_P9JBi-wgFUnp_1efTPnnVDYKQhIp6kTMyeA"/
    );
    expect(html).toMatch(/"@type":\s*"WebApplication"/);
    expect(html).toMatch(/alternateName/);
    expect(html).toMatch(/<h1>Blue Intelligence by Berry-Mappemonde<\/h1>/);
  });

  it("robots.txt et sitemap.xml statiques", () => {
    expect(existsSync(join(publicDir, "robots.txt"))).toBe(true);
    expect(existsSync(join(publicDir, "sitemap.xml"))).toBe(true);
    const robots = readFileSync(join(publicDir, "robots.txt"), "utf8");
    expect(robots).toMatch(/blueintelligence\.online\/sitemap\.xml/);
  });
});
