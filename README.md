# Model Cards

Model Cards generates documentation for AI models by bringing together information from Hugging Face repositories, technical reports and public evaluation records. The cards describe how a model was developed and evaluated, helping readers find information about its architecture, training and reported performance across these sources.

![Model card generation from source collection through evidence checks to the finished card](assets/model-card-pipeline.png)

Each card describes a specific model revision, and the pipeline checks whether the information it finds refers to that model, its base model or another model in the same family. It keeps copies of the sources and records why information was included or withheld, giving reviewers a way to examine the evidence and identify gaps in the documentation.

The generator builds on [Auto-BenchmarkCards](https://github.com/evaleval/auto-benchmarkcard) and produces structured JSON cards with matching Markdown versions for reading. A separate local inspection page links the generated content to its supporting evidence, while potential risks drawn from IBM’s AI Risk Atlas are included as suggestions for further review.

The repository contains [426 generated example cards](cards/) that have not yet undergone human review and are not official documentation from the model developers. They form the current working collection for the project, which is still being developed and evaluated.

The [usage guide](USAGE.md) explains how to install the generator and create a card, and the [architecture documentation](ARCHITECTURE.md) describes how the pipeline collects and checks its evidence.
