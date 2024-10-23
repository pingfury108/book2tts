from volcengine.visual.VisualService import VisualService
import base64


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")


def ocr_volc(ak, sk, file):
    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)
    # visual_service.set_host('host')
    action = "OCRNormal"
    #version = "2020-08-26"

    form = dict()
    form["image_base64"] = image_to_base64(file)

    resp = visual_service.ocr_api(action, form)
    if resp is not None:
        data = resp.get('data') or {}
        texts = data.get('line_texts') or []
        if len(texts) <= 0:
            print(resp)
            pass
        return "\n".join(texts)
    else:
        print(resp)
        return ""
