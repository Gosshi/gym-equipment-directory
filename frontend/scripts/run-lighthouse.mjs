import { spawn } from "node:child_process";
import { once } from "node:events";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const reportsDir = path.resolve(projectRoot, "lighthouse", "reports");
const port = Number.parseInt(process.env.LH_PORT ?? "3010", 10);

function startServer() {
  const server = spawn("npm", ["run", "start", "--", "-p", String(port)], {
    cwd: projectRoot,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, PORT: String(port) },
  });

  const readyPromise = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error("Timed out waiting for Next.js server to start"));
    }, 45_000);

    const onData = data => {
      const text = data.toString();
      if (text.toLowerCase().includes("started server")) {
        clearTimeout(timeout);
        server.stdout?.off("data", onData);
        server.stderr?.off("data", onError);
        resolve(undefined);
      }
    };

    const onError = data => {
      process.stderr.write(data);
    };

    server.stdout?.on("data", onData);
    server.stderr?.on("data", onError);

    server.once("exit", code => {
      clearTimeout(timeout);
      reject(new Error(`Next.js server exited prematurely (code ${code ?? "unknown"})`));
    });
  });

  return { server, readyPromise };
}

async function runLighthouse(targetUrl, reportName) {
  await mkdir(reportsDir, { recursive: true });
  const outputBase = path.join(reportsDir, reportName);
  const lighthouseBin = path.resolve(projectRoot, "node_modules", ".bin", "lighthouse");

  const args = [
    targetUrl,
    "--preset=desktop",
    "--output=json",
    "--output=html",
    `--output-path=${outputBase}`,
    "--quiet",
    "--chrome-flags=--headless=new --no-sandbox",
  ];

  const child = spawn(lighthouseBin, args, { stdio: "inherit" });
  const [code] = await once(child, "exit");
  if (code !== 0) {
    throw new Error(`Lighthouse failed for ${targetUrl} (exit code ${code})`);
  }

  const jsonPath = `${outputBase}.report.json`;
  const raw = await readFile(jsonPath, "utf-8");
  const data = JSON.parse(raw);
  const performance = data.categories?.performance?.score;
  const lcp = data.audits?.["largest-contentful-paint"]?.numericValue;
  const cls = data.audits?.["cumulative-layout-shift"]?.numericValue;
  const tti = data.audits?.["interactive"]?.numericValue;

  return {
    jsonPath,
    htmlPath: `${outputBase}.report.html`,
    performance,
    lcp,
    cls,
    tti,
  };
}

async function main() {
  const targets = [
    { name: "home", path: "/" },
    { name: "gyms", path: "/gyms" },
  ];

  const { server, readyPromise } = startServer();

  try {
    await readyPromise;

    const results = [];
    for (const target of targets) {
      const url = `http://127.0.0.1:${port}${target.path}`;
      const result = await runLighthouse(url, target.name);
      results.push({ target, result });
    }

    for (const { target, result } of results) {
      // eslint-disable-next-line no-console
      console.log(
        `Lighthouse (${target.path}) - Performance: ${(result.performance ?? 0) * 100}/100, ` +
          `LCP: ${result.lcp ?? 0}ms, CLS: ${result.cls ?? 0}, TTI: ${result.tti ?? 0}ms\n` +
          `Reports: ${path.relative(projectRoot, result.jsonPath)}, ${path.relative(projectRoot, result.htmlPath)}`,
      );
    }
  } finally {
    server.kill("SIGTERM");
    await once(server, "exit").catch(() => undefined);
  }
}

main().catch(error => {
  // eslint-disable-next-line no-console
  console.error(error);
  process.exitCode = 1;
});
