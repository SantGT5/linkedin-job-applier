export async function copyText(text: string) {
  await navigator.clipboard.writeText(text);
}

/** Copies rich text (links survive pasting into Gmail) with a plain-text fallback. */
export async function copyRich(html: string, text: string) {
  if (typeof ClipboardItem !== "undefined" && navigator.clipboard.write) {
    await navigator.clipboard.write([
      new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      }),
    ]);
  } else {
    await navigator.clipboard.writeText(text);
  }
}
