import torch
import re
from AuthorNet import AuthorNet

_DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

_CHECKPOINT = torch.load("Candidate_1_Adam_06701", map_location=_DEVICE)
_VOCAB = _CHECKPOINT['vocab']

_NET = AuthorNet(24, 11, _VOCAB).to(_DEVICE)
_NET.load_state_dict(_CHECKPOINT['model_state'])

_NET.eval()
  
_AUTHOR_DICT = {0: 106923035595948032,
                1: 106543824188264448,
                2: 93107928369762304,
                3: 129356159969656832,
                4: 81289959733985280,
                5: 93116437857603584,
                6: 210562031684812811,
                7: 196779392884539393,
                8: 94686558069719040,
                9: 113083395667464192,
                10: 106967980818042880}

def text_preprocess(msg_text):

    # Remove emotes
    msg = re.sub(r"([\<]).*?([\>])", "", msg_text).strip()

    # Pad punctuation with spaces
    msg = re.sub(r"([,.!?\(\)\[\]\{\}:;])", r" \1 ", msg)

    # Remove some markdown characters
    msg = re.sub(r"([`_*])", r"", msg)

    # lower case
    return msg.lower()

def msg_to_input(msg_text, hour, vocab):
    
    # One Hot Encoding of Hour
    hour_one_hot = [0]*24
    hour_one_hot[hour] = 1
    
    non_text_tensor = torch.tensor(hour_one_hot).float()

    # Preprocess text
    msg_text = text_preprocess(msg_text)

    # Tokenize Message
    tokens = msg_text.split()
    token_idx = [vocab.stoi[word]
                if word in vocab.stoi 
                else vocab.stoi["<unk>"]
                for word in tokens]

    return {'text': torch.tensor(token_idx, dtype = torch.long),
            'nontext': non_text_tensor}

def label_to_author_id(label, dict=_AUTHOR_DICT):
    return dict[label]


def get_best_author_id(msg_text, hour, net=_NET, vocab=_VOCAB, device = _DEVICE):

    with torch.no_grad():

        net.eval()
        
        obs_dict = msg_to_input(msg_text, hour, vocab)

        text = torch.unsqueeze(obs_dict["text"], 0).to(device)
        nontext = torch.unsqueeze(obs_dict["nontext"], 0).to(device)

        raw_out = net(text, nontext).squeeze()
        output = torch.nn.functional.softmax(raw_out)

        print(raw_out)

        predicted_value, predicted_label = output.max(0)

        author_id = label_to_author_id(predicted_label.item())

    return author_id, predicted_value.item()

if __name__ == "__main__":

    pred_author, pred_likelihood = get_best_author_id(
        "I pretty much did that 5 years ago.", 
        5)

    print(pred_author)
    print(pred_likelihood)
