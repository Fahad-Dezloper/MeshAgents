/* One-line rename: change `name` (and, if you like, `cli` and `dir`). Everything on the page reads from here.
   The repo URL is a PLACEHOLDER until the final one is decided. Empty video/blog links render as "coming soon". */
window.CONFIG = {
  name: "MeshAgents",
  tagline: "A shared memory for AI coding helpers.",
  repo: "https://github.com/Fahad-Dezloper/Baton", // PLACEHOLDER: the repo will be renamed; update this URL then
  repoIsPlaceholder: true,
  video: "",
  blog: "",
  heroCmd: "git clone {repo} {dir}",
  cli: "meshagents",
  dir: "meshagents",
  /* install commands, copied from the README; {repo} {cli} {dir} are filled in */
  install: [
    { label: "1. Get it and run the demo (no model, no API key; needs Docker and Python 3.10+)",
      cmd: "git clone {repo} {dir} && cd {dir}\ndocker compose up -d && python3 -m venv .venv && .venv/bin/pip install -e .\n.venv/bin/{cli} doctor && .venv/bin/python demo/run_demo.py" },
    { label: "2. Open the live board", cmd: ".venv/bin/{cli} ui   # then open http://127.0.0.1:7777" },
    { label: "3. Use it on your own project", cmd: "claude --plugin-dir /path/to/{dir}/plugin" }
  ]
};
