const $ = (id) => document.getElementById(id);
const statusEl = $("status");
const runButton = $("run");
runButton.addEventListener("click", async () => {
  const topic = $("topic").value.trim();
  if (topic.length < 8) { statusEl.textContent = "Please enter a research topic with at least 8 characters."; return; }
  const focus_questions = $("questions").value.split("\n").map(x => x.trim()).filter(Boolean);
  runButton.disabled = true; runButton.textContent = "Researching…"; statusEl.textContent = "Planner and research agents are working. This may take a little while.";
  try {
    const response = await fetch("/api/research", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic,audience:$("audience").value || "General audience",focus_questions,max_results_per_agent:5})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail?.error || data.detail || "Research request failed");
    render(data); statusEl.textContent = "Research completed.";
  } catch (error) { statusEl.textContent = `Error: ${error.message}`; }
  finally { runButton.disabled = false; runButton.innerHTML = 'Start research <span>↗</span>'; }
});
function render(data) {
  $("result").classList.remove("hidden");
  $("report-title").textContent = data.report?.title || data.topic;
  $("source-count").textContent = data.source_count; $("domain-count").textContent = data.unique_domain_count;
  $("coverage").textContent = `${data.coverage_score}%`; $("engine").textContent = data.workflow_engine;
  $("summary").textContent = data.report?.executive_summary || "No summary available.";
  $("critique").replaceChildren(...(data.critique || []).map(note => { const li=document.createElement("li"); li.textContent=note; return li; }));
  $("agents").replaceChildren(...(data.agent_trace || []).map(item => { const span=document.createElement("span"); span.className="agent"; span.textContent=`${item.agent}: ${item.message}`; return span; }));
  $("sources").replaceChildren(...(data.sources || []).map(source => {
    const item=document.createElement("div"); item.className="source";
    const link=document.createElement("a"); link.href=source.url; link.target="_blank"; link.rel="noopener noreferrer"; link.textContent=`[${source.source_id}] ${source.title}`;
    const snippet=document.createElement("p"); snippet.textContent=source.snippet;
    const meta=document.createElement("small"); meta.textContent=`${source.domain}${source.is_demo ? " · SYNTHETIC DEMO SOURCE" : ""}`;
    item.append(link,snippet,meta); return item;
  }));
  $("markdown").textContent = data.report?.markdown || "Report unavailable.";
  $("download").href = `/api/research/${data.run_id}/markdown`;
  $("result").scrollIntoView({behavior:"smooth",block:"start"});
}
