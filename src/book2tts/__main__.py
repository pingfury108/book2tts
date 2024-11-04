import click

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


cli.add_command(book_tts)

if __name__ == '__main__':
    cli()
