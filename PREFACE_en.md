# Preface

I wrote this book because I could never find the one I actually wanted.

When I joined the industry, what I received was the platform vendor's tuning documentation. The docs were thorough — which register controls which parameter, what happens when you increase a threshold, what happens when you decrease it. But I never understood the underlying logic. How do these parameters interact with each other? Why does the same setting work in one scene and break in another?

Later I moved to AE.

AE is, in my view, the hardest module in the ISP pipeline, without exception. The reason is simple: its evaluation endpoint is at the very end of the chain. By the time you see the result on screen, the signal has already passed through demosaicing, color correction, gamma, tonemapping, local enhancement. You have no idea whether the problem you're looking at lives in AE itself, or in how some downstream module handled the AE output. Worse, AE directly sets the exposure level, and exposure couples with color — the same image looks different at different gamma curves. The ground truth is in RAW, which your eyes cannot directly perceive.

AF is a different kind of problem. The core algorithm for fast focusing isn't particularly complex. What's hard is that "focus on what?" has never had a standard answer. In the same scene, different users want to focus on completely different subjects. You think you've tuned it well, someone else tests it, and they say it's hunting.

These experiences taught me something: tuning is not the goal — understanding the system is. Knowing *how* to adjust parameters without knowing *why* is the most common state in this industry.

---

## Who This Book Is For

This book is for two groups of people.

**Those new to the field**: engineers who want to understand what this pipeline actually does, not just follow documentation and change numbers.

**Tuning engineers moving toward systems engineering**: people who want a coherent system-level view — one that ties together algorithm, hardware, software, debugging, and evaluation.

This is not an algorithms textbook. There are no theorems, no proofs. It is closer to an annotated engineering map: what each module does, why it was designed that way, where it tends to fail, and how to evaluate whether it's working. If, after reading this book, you pause before changing a parameter and think through which stages it affects and what side effects it might trigger — the book has done its job.

---

## On System Thinking

I hold a view that may be unpopular, but I believe it's correct:

**System design matters more than algorithm choice. Algorithm choice matters more than hardware.**

That is not to say hardware doesn't matter. Sensor noise floor, lens resolution, SoC compute — these are real physical limits. But before those limits are properly understood and exploited, chasing hardware upgrades is cooking a better meal with better ingredients but not actually learning to cook.

The right cadence is: one hardware generation, paired with one generation of deep algorithmic and software tuning. Fully extract what the current hardware is capable of, and then you know where the next hardware generation needs to improve. Otherwise, every generation ships new hardware that leaves its potential only partially realized, problems accumulate, and debugging gets harder.

This argument depends on having a reliable image quality evaluation system. If your evaluation methodology is itself unstable — the same image scores 7 today and 5 tomorrow, and two engineers in the same team score it completely differently — then the word "optimization" loses meaning. Image quality evaluation is the most underestimated and most difficult piece of the whole system.

AI IQA is a popular direction in recent years. My assessment: technically worth learning and watching, but as a core production responsibility, it requires real caution at this stage. Without high-quality labeled data, and without a reliable path from evaluation conclusion to engineering action, the return on investment is not yet proportionate to the effort.

---

## On Deep Learning and What Comes Next

The traditional ISP algorithm framework evolved under severe compute constraints. A large fraction of its design decisions are "reasonable approximations with limited resources" rather than optimal solutions. Many modules are fundamentally rule-based logic applied to problems that are inherently non-linear.

Deep learning will first replace the modules that use rule-based logic to handle non-linearity. RAW-domain 3A perception and end-to-end raw-to-JPEG mapping are, in my view, the directions with the most potential. Not because they score well on benchmarks, but because they are addressing problems that traditional methods genuinely cannot solve.

Deployment is a separate question. On-device inference has power budgets, latency constraints, and thermal limits. In the chapters covering DL modules, this book tries to clearly distinguish between "paper result" and "deployable state" — being honest about which parts are current engineering practice and which remain in the research stage.

---

## How to Read This Book

Six volumes do not need to be read front to back.

If you are new to the field, start with Part 1 (Imaging Fundamentals) to build the physical and sensor model foundations, then move to Part 2 (Traditional ISP). These two parts are the foundation of everything else.

If you already have a background and want to understand DL in ISP, go directly to Part 3. For system design and quality evaluation, Part 4 is the focus. Parts 5 and 6 cover frontier directions and consumer-side engineering cases — read them as reference when relevant.

Each chapter follows the same structure: problem background → theory / mathematical model → algorithm / implementation → engineering practice → evaluation → code examples. Math formulas and code blocks are identical between the Chinese and English versions; they can be read in parallel directly.

---

## A Note on Openness

This book is open. Some content here has not been independently verified against internal test data; it relies on public benchmarks or published paper results, noted in the relevant sections. If you have more accurate data or different experiences from your own work, contributions via GitHub Issue or PR are welcome.

ISP is an intensely practical field. The best knowledge often lives in the heads of engineers who haven't written it down yet. If this book can serve as a starting point — one that encourages more people to put their experience into writing — that matters more than the book itself.

---

Cedar
Summer 2026
