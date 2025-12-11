# Usage

Run with uv, and pass flags to specify actions. For example, to run and put all files in a folder for today, 

```
uv run main --research --write --storyboard --film --produce
```

Some actions can take filters to restrict the amount of steps. For example, the following will research two targets, and film the first take.

```
uv run main --research vom tom --write --storyboard --film 0 --produce
```

# Notes

Sora 2 and Veo 3.1 generate very impressive videos, but it is hard to control the audio. For some reason, the audio always sounds robotic.

Neither of these let you upload audio.
