import { readFile, writeFile } from "node:fs/promises";
import { planVideo } from "./planner.mjs";
const args=process.argv.slice(2);
let text=args.join(" ");
if(!text) text=await readFile(0,"utf8");
const plan=planVideo(text);
const output=JSON.stringify(plan,null,2);
if(process.env.BAMO_PLAN_OUT) await writeFile(process.env.BAMO_PLAN_OUT,output+"\n");
process.stdout.write(output+"\n");
