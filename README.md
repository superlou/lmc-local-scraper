# Usage

Run with uv, and pass flags to specify actions. For example, to run and put all files in a folder for today, 

```
uv run main --research --write --storyboard --film --produce
```

Some actions can take filters to restrict the amount of steps. For example, the following will research two targets, write a script with 3 events, and film the first take.

```
uv run main --research vom tom --write 3 --storyboard --film 0 --produce
```

The options for actions are:

```
--research    list of targets from research.toml (default: all)
--write       number of events to include in the script (default: 4)
--storyboard  (no options)
--film        list of take IDs from storyboard.toml (default: all)
--produce     (no options)
```

# Notes

Sora 2 and Veo 3.1 generate very impressive videos, but it is hard to control the audio. For some reason, the audio always sounds robotic.

Neither of these let you upload audio.
