import fs from "fs";
import path from "path";

// The Projects row: the fly-to button and the external link must be siblings
// (no interactive control nested in another), link after the button in DOM order.
const src = fs.readFileSync(path.join(__dirname, "..", "ProjectList.js"), "utf8");

describe("ProjectList row markup", () => {
  test("the external link is not nested inside the row button", () => {
    const buttonOpen = src.indexOf("<button");
    const buttonClose = src.indexOf("</button>", buttonOpen);
    const link = src.indexOf("<a", buttonOpen);
    expect(buttonOpen).toBeGreaterThan(-1);
    expect(link).toBeGreaterThan(buttonClose);
  });

  test("the link follows the button and is labelled", () => {
    expect(src).toContain('aria-label={`${f.properties.title}: ${t("projectOpenPage")}`}');
    expect(src).not.toContain("e.stopPropagation()");
  });
});
