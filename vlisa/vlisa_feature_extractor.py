import re
import os
import copy
import json
import random
import base64
import requests
import argparse
import pandas as pd
from tqdm import tqdm
from openai import OpenAI


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def gpt4o_pred(model_config, system_prompt, query, base64_image, mode, max_len):
    
    client = OpenAI(api_key = model_config['key'],
                    base_url = "your base url")
    
    if mode=="naive":
        response = client.chat.completions.create(
            model=model_config['name'],
            messages=[
                # {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                },
            ],
            max_tokens=max_len
        )
    elif mode=="cot":
        response = client.chat.completions.create(
            model=model_config['name'],
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                },
            ],
            max_tokens=max_len
        )
    return response.choices[0].message.content.strip()


def pred(annotation_file, img_folder, output_file, mode, max_len):

    # data
    ann_file_df = pd.read_csv(annotation_file) 
    img_list = ann_file_df['file_name'].tolist()

    # model
    gpt4o = {"name": "gpt-4o", "key": "Your API key here."}

    if mode=="naive":
        system = ""
        user_prompt = "Describe this image in detail." 
    elif mode=="cot":
        system_prompt_path = 'cot_description_system.txt'
        system = open(system_prompt_path, encoding="utf-8").read()  

        user_prompt = "Please first identify the different visual clues in the image and then infer the corresponding information based on these visual clues. Finally, describe the story occurring in the image based on the inferred information." 

    response = {}
    for filename in tqdm(img_list):
        print(filename)

        img_path = img_folder + "/{}".format(filename)
        base64_image = encode_image(img_path)

        output = gpt4o_pred(gpt4o, system, user_prompt, base64_image, mode, max_len)
        print(output)

        response['file_name'] = filename
        response['model_output'] = output

        entity_score = ann_file_df[ann_file_df['file_name']==filename]['entity_score'].tolist()[0]
        semantic_score = ann_file_df[ann_file_df['file_name']==filename]['semantic_score'].tolist()[0]
        response['entity_score'] = entity_score
        response['semantic_score'] = semantic_score

        with open(output_file, "a") as wf:
            json.dump(response, wf)
            wf.write('\n')

    print("DONE!")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotation_file",
        type=str,
        default="/path/to/annotation_file.csv",
    )
    parser.add_argument(
        "--image_folder",
        type=str,
        default="/path/to/image_folder",
    )
    parser.add_argument(
        "--model_output_file",
        type=str,
        default="/path/to/model_output_feature_file.jsonl",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="naive",
    )
    parser.add_argument(
        "--max_len",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    pred(args.annotation_file, args.image_folder, args.model_output_file, args.mode, args.max_len)
    