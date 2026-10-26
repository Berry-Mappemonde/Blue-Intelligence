import { reviewToggleClass, reviewToggleLabelClass } from "../headerState";

describe("Show review toggle", () => {
  test("pressed state carries the accent so an accidental 'on' is visible", () => {
    const on = reviewToggleClass(true);
    const off = reviewToggleClass(false);
    expect(on).toContain("border-m-accent");
    expect(on).toContain("text-m-accent-fg");
    expect(off).not.toContain("m-accent");
    expect(on).not.toBe(off);
  });

  test("label stays visible whenever the toggle is on", () => {
    expect(reviewToggleLabelClass(true)).toBe("inline");
    expect(reviewToggleLabelClass(false)).toContain("hidden");
  });
});
