import {readFile,writeFile} from "node:fs/promises";
import {compileTimeline,validateTimeline} from "./timeline.mjs";
const file=process.argv[2];if(!file)throw new Error("Usage: node src/timeline-cli.mjs alignment.json");
const input=JSON.parse(await readFile(file,"utf8"));
const timeline=compileTimeline(input.sceneGraph,input.wordEvents,input.audioDuration);
const check=validateTimeline(timeline);if(!check.ok)throw new Error(check.errors.join("; "));
const output=JSON.stringify(timeline,null,2);if(process.env.BAMO_TIMELINE_OUT)await writeFile(process.env.BAMO_TIMELINE_OUT,output+"\n");process.stdout.write(output+"\n");
