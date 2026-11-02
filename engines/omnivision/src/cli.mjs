import { writeFile } from "node:fs/promises";
import { planVideo } from "./planner.mjs";
const args = process.argv.slice(2);
let script = args.join(" ");
if (!script) {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  script = Buffer.concat(chunks).toString("utf8");
}
const plan = planVideo(script);
const output = JSON.stringify(plan, null, 2);
if (process.env.BAMO_PLAN_OUT) await writeFile(process.env.BAMO_PLAN_OUT, output + "\n");
process.stdout.write(output + "\n");
