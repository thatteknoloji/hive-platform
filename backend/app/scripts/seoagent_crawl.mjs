import { auditCrawl, auditReport, auditPage } from "@seoagent/core";

const [cmd, ...args] = process.argv.slice(2);

async function main() {
  try {
    if (cmd === "crawl") {
      const [domain, maxPages] = args;
      const result = await auditCrawl(domain, {
        maxPages: parseInt(maxPages || "500"),
        concurrency: 5,
      });
      console.log(JSON.stringify(result));
    } else if (cmd === "audit") {
      const url = args[0];
      const result = await auditPage(url);
      console.log(JSON.stringify(result));
    } else {
      console.error('Unknown command: ' + cmd);
      process.exit(1);
    }
  } catch (err) {
    console.error(JSON.stringify({ error: err.message }));
    process.exit(1);
  }
}

main();
