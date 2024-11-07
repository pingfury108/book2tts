import os
import click
import tempfile
import ffmpeg

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
def merge_audio(dirname, outfile):
    input_files = [
        os.path.join(dirname, f) for f in sorted(os.listdir(dirname))
    ]
    _, tmp_file = tempfile.mkstemp()
    print(tmp_file)
    with open(tmp_file, 'w') as f:
        f.write("\n".join(
            [f"file '{audio_file}'" for audio_file in input_files]))
    ffmpeg.input(tmp_file, format='concat',
                 safe=0).output(outfile, format='wav', acodec='copy').run()
    os.remove(tmp_file)
    return


cli.add_command(book_tts)
cli.add_command(merge_audio)

if __name__ == '__main__':
    cli()
