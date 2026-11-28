/** Print local course Markdown/HTML with tools supplied by npx, without repo dependencies. */
import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir, homedir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [inputArg, outputArg, ...options] = process.argv.slice(2);
if (!inputArg || !outputArg)
  throw new Error("Usage: render_course_pdf.mjs INPUT OUTPUT [--slides]");
const input = path.resolve(inputArg);
const output = path.resolve(outputArg);
const cliPath = realpathSync(
  execFileSync("which", ["mmdc"], { encoding: "utf8" }).trim(),
);
const requireTool = createRequire(cliPath);
const { default: puppeteer } = await import(
  pathToFileURL(requireTool.resolve("puppeteer")).href
);
const { marked, Renderer } = await import(
  pathToFileURL(requireTool.resolve("marked")).href
);
const temporary = mkdtempSync(path.join(tmpdir(), "course-print-"));
const escape = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

function executablePath() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH)
    return process.env.PUPPETEER_EXECUTABLE_PATH;
  for (const name of ["chromium", "chromium-browser", "google-chrome"]) {
    try {
      return execFileSync("which", [name], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
    } catch {
      /* Try the next supported system browser. */
    }
  }
  const cache = path.join(homedir(), ".cache/ms-playwright");
  try {
    const found = execFileSync(
      "find",
      [cache, "-type", "f", "-name", "chrome"],
      { encoding: "utf8" },
    )
      .trim()
      .split("\n")
      .filter(Boolean);
    if (found.length) return found.sort().at(-1);
  } catch {
    /* The documented environment override remains available. */
  }
  throw new Error(
    "Set PUPPETEER_EXECUTABLE_PATH to an installed Chromium executable",
  );
}

let browser;
try {
  const config = { executablePath: executablePath(), args: ["--no-sandbox"] };
  writeFileSync(path.join(temporary, "puppeteer.json"), JSON.stringify(config));
  let htmlPath = input;
  if (path.extname(input).toLowerCase() !== ".html") {
    let markdown = readFileSync(input, "utf8");
    if (/```mermaid\s|:::mermaid\s/.test(markdown)) {
      const rendered = path.join(temporary, "rendered.md");
      execFileSync(
        cliPath,
        [
          "-i",
          input,
          "-o",
          rendered,
          "-a",
          temporary,
          "-e",
          "svg",
          "-j",
          "2",
          "-p",
          path.join(temporary, "puppeteer.json"),
        ],
        {
          stdio: "inherit",
          env: { ...process.env, PUPPETEER_SKIP_DOWNLOAD: "true" },
        },
      );
      markdown = readFileSync(rendered, "utf8");
    }
    const renderer = new Renderer();
    renderer.image = ({ href, title, text }) => {
      let url = href;
      if (!/^(?:data:|https?:|file:)/i.test(href)) {
        const decoded = decodeURIComponent(href);
        const generated = path.resolve(temporary, decoded);
        const original = path.resolve(path.dirname(input), decoded);
        const local = existsSync(generated) ? generated : original;
        if (!existsSync(local)) throw new Error(`Missing image: ${local}`);
        url = pathToFileURL(local).href;
      }
      return `<img src="${escape(url)}" alt="${escape(text)}"${title ? ` title="${escape(title)}"` : ""}>`;
    };
    const content = await marked.parse(markdown, { renderer });
    const isContribution = path.basename(input) === "15-contribution.md";
    const style = `@page{size:A4;margin:14mm}*{box-sizing:border-box}body{font:10pt/1.4 Arial,sans-serif;color:#16302e;margin:0}h1{font-size:22pt;color:#0f766e;margin:0 0 8mm}h2{font-size:15pt;margin:7mm 0 3mm;break-after:avoid}h3{font-size:12pt;break-after:avoid}p,li{orphans:3;widows:3}table{border-collapse:collapse;width:100%;font-size:8.8pt;margin:4mm 0}th,td{border:1px solid #d6d3d1;padding:1.4mm 1.6mm;vertical-align:top;overflow-wrap:anywhere}th{background:#f0fdfa;color:#115e59}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:8pt/1.3 monospace;background:#f5f5f4;padding:3mm}code{font-size:.9em}a{color:#0f766e;text-decoration:none}img{display:block;max-width:100%;max-height:245mm;object-fit:contain;margin:4mm auto;break-inside:avoid}blockquote{border-left:3px solid #0f766e;margin-left:0;padding-left:4mm;color:#57534e}${isContribution ? "h2{break-before:page}" : ""}`;
    htmlPath = path.join(temporary, "document.html");
    writeFileSync(
      htmlPath,
      `<!doctype html><html><head><meta charset="utf-8"><title>${escape(path.basename(input))}</title><style>${style}</style></head><body>${content}</body></html>`,
    );
  }
  browser = await puppeteer.launch(config);
  const page = await browser.newPage();
  await page.setJavaScriptEnabled(false);
  await page.setRequestInterception(true);
  page.on("request", (request) =>
    /^(?:file:|data:)/.test(request.url())
      ? request.continue()
      : request.abort(),
  );
  await page.goto(pathToFileURL(htmlPath).href, {
    waitUntil: "networkidle0",
    timeout: 90000,
  });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: output,
    printBackground: true,
    preferCSSPageSize: true,
    ...(options.includes("--slides") ? {} : { format: "A4" }),
  });
  console.log(`PDF exported: ${output}`);
} finally {
  if (browser) await browser.close();
  rmSync(temporary, { recursive: true, force: true });
}
