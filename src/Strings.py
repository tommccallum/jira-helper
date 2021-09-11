def convertSnakeCaseToCamelCase(name):
    if "_" in name:
        name = ''.join(word.title() for word in name.split('_'))
        name = name[:1].lower() + name[1:]
    return name

