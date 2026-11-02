import { writeFile } from "node:fs/promises";
import { planVideo } from "./planner.mjs";
import { compileSceneGraph, validateSceneGraph } from "./scene-graph.mjs";
const args=process.argv.slice(2);
let script=args.join(" ");
if(!script){const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);script=Buffer.concat(chunks).toString("utf8");}
const graph=compileSceneGraph(planVideo(script));
const result=validateSceneGraph(graph);
if(!result.ok){process.stderr.write(JSON.stringify(result.errors)+"\n");process.exit(1);}
const output=JSON.stringify(graph,null,2);
if(process.env.BAMO_GRAPH_OUT) await writeFile(process.env.BAMO_GRAPH_OUT,output+"\n");
process.stdout.write(output+"\n");
