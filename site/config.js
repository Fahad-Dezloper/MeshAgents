/* One-line rename: change `name` (and, if you like, `cli` and `dir`). Everything on the page reads from here.
   Empty video/blog links render as "coming soon". */
window.CONFIG = {
  name: "MeshAgents",
  tagline: "A shared memory for AI coding agents.",
  repo: "https://github.com/Fahad-Dezloper/MeshAgents",
  repoIsPlaceholder: false,
  video: "",
  blog: "",
  heroCmd: "git clone {repo}",
  cli: "meshagents",
  dir: "meshagents",
  /* three steps; {repo} {cli} {dir} are filled in */
  steps: [
    { label: "Get it", cmd: "git clone {repo}" },
    { label: "Check it", cmd: "{cli} doctor" },
    { label: "Use it", cmd: "claude --plugin-dir ./plugin" }
  ],
  after: "Then run {cli} ui to watch your agents live."
};
