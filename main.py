#!python3
# author: Karl Jan Clinckspoor
# start date: 2020-12-08
# last update: 2020-12-08

from config import thesis_path, stats_basepath
from repo_info import create_commit_list
from text_stats import Stats
import pathlib
import git
import glob
import os
import shutil
from typing import List
import subprocess


def main():
    # Step 1: Extract information from the directory
    print(thesis_path)
    print("Creating commit list", end="")
    create_commit_list()
    print(" - Done")


def create_stats_from_sha(
    sha: str,
    repo: git.Repo,
    filename_pattern: str = "*.tex",
    merge: bool = True,
) -> List[Stats]:
    from text_stats import open_file

    starting_sha = repo.commit().hexsha
    repo.git.checkout(sha)
    date = repo.commit().committed_date

    path = pathlib.Path(thesis_path)
    tex_files = glob.glob(str(path / filename_pattern))
    assert len(tex_files) >= 1

    if merge:
        list_text: List[str] = []
        for file in tex_files:
            text = open_file(file)
            list_text.append(text)
        full_text = "\n".join(list_text)
        st = Stats(
            f"all",
            text=full_text,
            commit_hash=sha,
            description="",
            date=date,
            output_path=stats_basepath,
        )
        st.calculate_stats()
        return [st]
    else:
        list_stats: List[Stats] = []
        for file in tex_files:
            text = open_file(file)
            st = Stats(
                file,
                text=full_text,
                commit_hash=sha,
                description=filename_pattern,
                output_path=str(pathlib.Path(stats_basepath) / sha),
                debug_output_path=str(pathlib.Path(stats_basepath) / sha),
            )
            list_stats.append(st)
        return list_stats

    repo.git.checkout(starting_sha)


def compile_pdf_from_sha(
    sha: str,
    output_path: str,
    repo: git.Repo,
    texfile_location: str,
    fix_includeonly: bool = True,
) -> None:
    # TODO: Make commands more generic
    starting_sha = repo.commit().hexsha
    repo.git.checkout(sha, force=True)
    # It's easier to change dirs because of the latex commands, copy the pdf,
    # then change back
    xelatex_command = [
        "xelatex",
        "-shell-escape",
        # "output-directory='../FilmeTese/pdfs'",
        "-interaction=nonstopmode",
        "main.tex",
    ]
    makeindex_command = ["makeindex", "main.tex"]
    bibtex_command = ["bibtex", "main"]

    # Check if there's already a pdf file there
    if os.path.isfile(f"./pdfs/{sha}.pdf"):
        print(f"Already compiled {sha}")
        return

    os.chdir("../Tese")

    # I didn't see any case of includeonlys
    if fix_includeonly:
        maintex = open("main.tex", "r").read()
        # Very crude
        maintex.replace("includeonly", "")
        with open("main.tex", "w") as fhand:
            fhand.write(maintex)

    # One specific commit had a problem, where there was a table in the file
    # "aditivos.tex" where the first cell title was [NaSal], and the previous
    # command was \toprule. Even with the newline between them, xelatex was
    # considering it to be \toprule[NaSal], and accusing NaSal of not being a
    # number, freezing compilation.
    if sha.startswith("df17dbd"):
        problematic_text = open("aditivos.tex", "r").read()
        import re

        problematic_text = re.sub(
            r"\\toprule([\s%]+?)\[NaSal\]",
            r"\\toprule\1NaSal",
            problematic_text,
        )
        with open("aditivos.tex", "w") as fhand:
            fhand.write(problematic_text)

    print("\tCompilation 1", flush=True)
    proc = subprocess.run(xelatex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print("\tIndex", flush=True)
    proc = subprocess.run(makeindex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print("\tReferences", flush=True)
    proc = subprocess.run(bibtex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print("\tCompilation 2", flush=True)
    proc = subprocess.run(xelatex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print("\tCompilation 3", flush=True)
    proc = subprocess.run(xelatex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print("\tCompilation 4", flush=True)
    proc = subprocess.run(xelatex_command, capture_output=False)
    # write_logfiles(proc, log, err)

    print(flush=True)
    print("\tCompilation done", flush=True)

    shutil.copy("main.pdf", f"../FilmeTese/pdfs/{sha}.pdf")

    os.chdir("../FilmeTese")
    repo.git.checkout(starting_sha, force=True)


def test_create_all_stats():
    from repo_info import load_commit_list

    commits = load_commit_list()
    starting_commit = commits[0]["sha"]
    repo = git.Repo(thesis_path)
    repo.git.checkout(starting_commit, force=True)

    for commit in commits:
        st = create_stats_from_sha(
            commit["sha"],
            repo,
        )[0]
        st.pickle()
        st.save_as_text()


def test_compile_all_pdfs():
    from repo_info import load_commit_list

    commits = load_commit_list()
    starting_commit = commits[0]
    repo = git.Repo(thesis_path)
    for i, commit in enumerate(commits):
        print(
            f'Compilation {i+1} of {len(commits)}: {commit["message"]}',
            flush=True,
        )
        compile_pdf_from_sha(commit["sha"], "./pdfs", repo, "../Tese")


def test_all_includeonlys():
    from repo_info import load_commit_list

    commits = load_commit_list()
    repo = git.Repo(thesis_path)
    for i, commit in enumerate(commits):
        print(
            f'Problem in {commit["sha"]}? {test_includeonly(commit["sha"], repo)}'
        )


def test_includeonly(sha: str, repo: git.Repo) -> str:
    repo.git.checkout(sha, force=True)
    maintex = open("../Tese/main.tex", "r").readlines()
    for line in maintex:
        if "includeonly" in line:
            return line
    # for line in maintex:
    #     if line.strip().startswith(r"\includeonly"):
    #         return "\n" + line
    # else:
    #     return False
    # maintex.replace("includeonly", "")


# test_create_all_stats()
# test_compile_all_pdfs()
test_all_includeonlys()

# if __name__ == "__main__":
#     main()
