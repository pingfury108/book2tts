import os
import re
import click
import tempfile
import ffmpeg
from pathlib import Path

from book2tts.parse import (parse_epub)


@click.group
def cli():
    pass


@click.command()
@click.argument('filename')
@click.argument('datadir')
def book_tts(filename, datadir):
    click.echo(filename)
    book = parse_epub(filename)
    book.save(datadir)
    return


@click.command()
@click.argument('dirname')
@click.argument('outfile')
@click.option('--num_sort / --no-num_sort',
              default=False,
              help='Number sorted',
              type=bool)
def merge_audio(dirname, outfile, num_sort):
    input_files = [
        os.path.join(dirname, f) for f in sorted(os.listdir(dirname), )
    ]
    if num_sort:
        input_files = sorted(
            input_files, key=lambda s: int("".join(re.findall(r'(\d+)', s))))
    click.echo(input_files)

    _, tmp_file = tempfile.mkstemp()
    print(tmp_file)
    with open(tmp_file, 'w') as f:
        f.write("\n".join(
            [f"file '{audio_file}'" for audio_file in input_files]))

    ffmpeg.input(tmp_file, format='concat',
                 safe=0).output(outfile, format='wav', acodec='copy').run()
    #os.remove(tmp_file)
    return


@click.command()
@click.argument('dirname')
def audio_duration(dirname):
    input_files = [
        os.path.join(dirname, f) for f in sorted(os.listdir(dirname))
        if f.endswith(".wav") or f.endswith(".mp3")
    ]

    count = 0.0

    for file in input_files:
        # 使用 ffmpeg.probe 获取音频文件的元数据
        probe = ffmpeg.probe(file)

        # 查找音频流并获取时长
        audio_stream = next((stream for stream in probe['streams']
                             if stream['codec_type'] == 'audio'), None)

        if audio_stream is not None:
            duration = float(audio_stream['duration'])
            count += duration
            print(f"{file}: {duration}")
        else:
            print("未找到音频流")

    click.echo(f"音频时长: {count:.2f} 秒")
    click.echo(f"音频时长: {count/60:.2f} 分")
    click.echo(f"音频时长: {count/3600:.2f} 时")

    return


cli.add_command(book_tts)
cli.add_command(merge_audio)
cli.add_command(audio_duration)

if __name__ == '__main__':
    cli()
