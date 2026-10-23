import { formatSize } from "./format";

test("formatSize", () => {
  expect(formatSize(193)).toBe("193 bytes");
  expect(formatSize(1536)).toBe("1.5 KB");
  expect(formatSize(1_258_291)).toBe("1.2 MB");
});
