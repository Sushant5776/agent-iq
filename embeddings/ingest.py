from chunking import chunk_text_from_file


def main(file_path: str):
    chunk_obj = chunk_text_from_file(file_path=file_path)
    print(chunk_obj["file_name"])
    print(chunk_obj["chunks"])


if __name__ == "__main__":
    file_path = input("Enter file path: ")
    main(file_path=file_path)
