import { api } from "../shared/api.js";
import { $ } from "../shared/dom.js";
import { toast } from "../shared/toast.js";

export function render(state) {
  const integrity = $("#integrity");
  const broken = state.integrity.problems.length > 0;
  integrity.className = `badge ${broken ? "bad" : "ok"}`;
  integrity.textContent = broken ? "Log has been altered" : `Log intact · ${state.integrity.entries} entries`;
  integrity.title = broken ? state.integrity.problems.join("\n") : "Click to also check the full git history";
}

export function wire() {
  $("#integrity").addEventListener("click", async () => {
    toast("Checking the full history…");
    try {
      const { problems } = await api("/api/verify");
      toast(problems.length ? `Altered: ${problems.join("; ")}` : "Intact: every entry is sealed to the one before, and no commit rewrote an earlier one.", problems.length ? "bad" : "");
    } catch (error) {
      toast(error.message, "bad");
    }
  });
}
