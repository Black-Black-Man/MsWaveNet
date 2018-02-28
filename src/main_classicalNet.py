""" usage:
    python main.py
    python main.py --network=dnn --mode=test --model='../model/dnn_mix.pkl'

"""
import argparse
import time
from network import *
from data_process import *
import os

# Training settings
parser = argparse.ArgumentParser(description='pytorch model')
parser.add_argument('--batch-size', type=int, default=32, metavar='N',
                            help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=18, metavar='N',
                            help='input batch size for testing (default: 5)')
parser.add_argument('--epochs', type=int, default=180, metavar='N',
                            help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                            help='learning rate (default: 0.001)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                            help='SGD momentum (default: 0.9)')
parser.add_argument('--weight_decay', type=float, default=5e-4, metavar='M',
                            help='weight decay')
parser.add_argument('--no-cuda', action='store_true', default=False,
                            help='disables CUDA training')
parser.add_argument('--gpu', type=list, default=[4,5,6,7],
                            help='gpu device number')
parser.add_argument('--seed', type=int, default=777, metavar='S',
                            help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=20, metavar='N',
                            help='how many batches to wait before logging training status')
parser.add_argument('--model_save_interval', type=int, default=40, metavar='N',
                            help='how many epochs to wait before saving the model.')
parser.add_argument('--network', type=str, default='ResNet18_lrf',
                            help='EnvNet or EnvNet_mrf or EnvNet_lrf or EnvNet3D or EnvNetMultiScale')
parser.add_argument('--mode', type=str, default='train',
                            help='train or test')
parser.add_argument('--model', type=str, default='../model/EnvNet_v1_fold0_v2_epoch120.pkl',
                            help='trained model path')
parser.add_argument('--train_slices', type=int, default=1,
                            help='slices number of one record divide into.')
parser.add_argument('--test_slices_interval', type=int, default=0.2,
                            help='slices number of one record divide into.')
parser.add_argument('--fs', type=int, default=44100)


os.environ['CUDA_VISIBLE_DEVICES'] = "1"

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

#  torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)
    #  torch.cuda.set_device(2)


def train_p1(model, optimizer, train_loader, epoch):
#{{{
    model.train()
    start = time.time()

    running_loss = 0
    running_correct = 0

    for idx, (data, label) in enumerate(train_loader):

        #  reshape to torch.LongTensor of size 64
        label = label.resize_(label.size()[0])

        if args.cuda:
            data, label = data.cuda(), label.cuda()
        data, label = Variable(data), Variable(label)

        optimizer.zero_grad()

        # print data.size()
        output = model(data) # (batch, 50L)
        # print(label)
        # print output.size()
        # exit(0)
        loss = F.cross_entropy(output, label)
        #  loss = F.nll_loss(output, label)

        loss.backward()

        optimizer.step()
        _, pred = torch.max(output.data, 1)  # get the index of the max log-probability

        # statistics
        running_loss += loss.data[0]
        running_correct += torch.sum(pred == label.data.view_as(pred))

    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100.0 * running_correct / len(train_loader.dataset)

    elapse = time.time() - start

    print('Phase1 Epoch:{} ({:.1f}s) lr:{:.4g}  '
          'samples:{}  Loss:{:.3f}  TrainAcc:{:.2f}%'.format(
        epoch, elapse, optimizer.param_groups[0]['lr'],
        len(train_loader.dataset), epoch_loss, epoch_acc))


def train_p2(model, optimizer, train_loader, epoch):
#{{{
    model.train()
    start = time.time()

    running_loss = 0
    running_correct = 0

    for idx, (data, feats, label) in enumerate(train_loader):

        #  reshape to torch.LongTensor of size 64
        label = label.resize_(label.size()[0])

        if args.cuda:
            data, feats, label = data.cuda(), feats.cuda(), label.cuda()
        data, feats, label = Variable(data), Variable(feats), Variable(label)

        optimizer.zero_grad()

        # print data.size()
        output = model(data, feats)
        # print(label)
        # print output.size()
        # exit(0)
        loss = F.cross_entropy(output, label)
        #  loss = F.nll_loss(output, label)

        loss.backward()

        optimizer.step()

        _, pred = torch.max(output.data, 1)  # get the index of the max log-probability

        # statistics
        running_loss += loss.data[0]
        running_correct += torch.sum(pred == label.data.view_as(pred))

    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100.0 * running_correct / len(train_loader.dataset)

    elapse = time.time() - start

    print('Phase2 Epoch:{} ({:.1f}s) lr:{:.4g}  '
          'samples:{}  Loss:{:.3f}  TrainAcc:{:.2f}%'.format(
        epoch, elapse, optimizer.param_groups[0]['lr'],
        len(train_loader.dataset), epoch_loss, epoch_acc))


#}}}


def test_p1(model, test_pkl, fs):
#{{{
    model.eval()

    start = time.time()

    test_loss = 0
    correct = 0

    win_size = int(fs * 1.5)
    stride = int(fs * args.test_slices_interval)
    sampleSet = load_data(test_pkl)

    for item in sampleSet:
        label = item['label']
        record_data = item['data']
        wins_data = []
        for j in range(0, len(record_data) - win_size + 1, stride):

            win_data = record_data[j: j+win_size]
            # Continue if cropped region is silent

            maxamp = np.max(np.abs(win_data))
            if maxamp < 0.005:
                continue
            wins_data.append(win_data)

        if len(wins_data) == 0:
            print(item['key'])

        wins_data = np.array(wins_data)

        wins_data = wins_data[:, np.newaxis, :]
        # print wins_data.shape

        data = torch.from_numpy(wins_data).type(torch.FloatTensor) # (N, 1L, 24002L)
        label = torch.LongTensor([label])

        if args.cuda:
            data, label = data.cuda(), label.cuda()
        data, label = Variable(data, volatile=True), Variable(label)

        # print data.size()
        output = model(data)
        output = torch.sum(output, dim=0, keepdim=True)
        # print output

        test_loss += F.cross_entropy(output, label).data[0] # sum up batch loss
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        correct += pred.eq(label.data.view_as(pred)).sum()

    test_loss /= len(sampleSet)
    test_acc = 100. * correct / len(sampleSet)

    elapse = time.time() - start

    print('\nTest set: Average loss: {:.3f} ({:.1f}s), TestACC: {}/{} {:.2f}%\n'.format(
        test_loss, elapse, correct, len(sampleSet), test_acc))

    return test_acc

def test_p2(model, test_pkl, fs):
#{{{
    model.eval()

    start = time.time()

    test_loss = 0
    correct = 0

    win_size = int(fs * 1.5)
    stride = int(fs * args.test_slices_interval)
    sampleSet = load_data(test_pkl)

    for item in sampleSet:
        label = item['label']
        record_data = item['data']
        wins_data = []
        feats = []
        for j in range(0, len(record_data) - win_size + 1, stride):

            win_data = record_data[j: j+win_size]
            # Continue if cropped region is silent

            maxamp = np.max(np.abs(win_data))
            if maxamp < 0.005:
                continue
            wins_data.append(win_data)

            melspec = librosa.feature.melspectrogram(win_data, 44100, n_fft=2048, hop_length=150, n_mels=96)  # (40, 442)
            logmel = librosa.logamplitude(melspec)[:,:441]  # (40, 441)
            # mfcc = librosa.feature.mfcc(win_data, n_fft=2048, hop_length=150, sr=44100, n_mfcc=32)
            # mfcc = mfcc[:,:441]
            # delta = librosa.feature.delta(logmel)  # (40, 441)
            # feat = np.stack((logmel, mfcc, delta))
            feat = logmel[np.newaxis, :, :]
            feats.append(feat)

        if len(wins_data) == 0:
            print(item['key'])

        wins_data = np.array(wins_data)
        feats = np.array(feats)

        wins_data = wins_data[:, np.newaxis, :]
        # print wins_data.shape

        data = torch.from_numpy(wins_data).type(torch.FloatTensor) # (N, 1L, 24002L)
        feats = torch.from_numpy(feats).type(torch.FloatTensor)
        label = torch.LongTensor([label])

        if args.cuda:
            data, feats, label = data.cuda(), feats.cuda(), label.cuda()
        data, feats, label = Variable(data, volatile=True), Variable(feats, volatile=True), Variable(label)

        # print data.size()
        output = model(data, feats)
        output = torch.sum(output, dim=0, keepdim=True)
        # print output

        test_loss += F.cross_entropy(output, label).data[0] # sum up batch loss
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        correct += pred.eq(label.data.view_as(pred)).sum()

    test_loss /= len(sampleSet)
    test_acc = 100. * correct / len(sampleSet)

    elapse = time.time() - start

    print('\nTest set: Average loss: {:.3f} ({:.1f}s), TestACC: {}/{} {:.2f}%\n'.format(
        test_loss, elapse, correct, len(sampleSet), test_acc))

    return test_acc

def main_on_fold(foldNum, trainPkl, validPkl):

    # --------phase 1:----------
    if args.network == 'M9_srf_fixed_logmel':
        model = M9_srf_fixed_logmel(phase=1)
    elif args.network == 'M9_mrf_fixed_logmel':
        model = M9_mrf_fixed_logmel(phase=1)
    elif args.network == 'M9_lrf_fixed_logmel':
        model = M9_lrf_fixed_logmel(phase=1)
    elif args.network == 'M9_fixed_logmel':
        model = M9_fixed_logmel(phase=1)
    elif args.network == 'MsResNet':
        model = MsResNet(Bottleneck, [3, 4, 6, 3], phase=1, num_classes=50)
    elif args.network == 'MsResNet_lrf':
        model = MsResNet_lrf(Bottleneck, [3, 4, 6, 3], phase=1, num_classes=50)
    elif args.network == 'MsResNet_srf':
        model = MsResNet_srf(Bottleneck, [3, 4, 6, 3], phase=1, num_classes=50)
    elif args.network == 'MsResNet_mrf':
        model = MsResNet_mrf(Bottleneck, [3, 4, 6, 3], phase=1, num_classes=50)
    elif args.network == 'vgg11_bn':
        model = vgg11_bn(phase=1, num_classes=50)
    elif args.network == 'vgg11_bn_srf':
        model = vgg11_bn_srf(phase=1, num_classes=50)
    elif args.network == 'vgg11_bn_mrf':
        model = vgg11_bn_mrf(phase=1, num_classes=50)
    elif args.network == 'vgg11_bn_lrf':
        model = vgg11_bn_lrf(phase=1, num_classes=50)
    elif args.network == 'alexnet':
        model = AlexNet(phase=1, num_classes=50)
    elif args.network == 'alexnet_srf':
        model = AlexNet_srf(phase=1, num_classes=50)
    elif args.network == 'alexnet_mrf':
        model = AlexNet_mrf(phase=1, num_classes=50)
    elif args.network == 'alexnet_lrf':
        model = AlexNet_lrf(phase=1, num_classes=50)
    elif args.network == 'ResNet18':
        model = ResNet18(BasicBlock, [2, 2, 2, 2], phase=1, num_classes=50)
    elif args.network == 'ResNet18_srf':
        model = ResNet18_srf(BasicBlock, [2, 2, 2, 2], phase=1, num_classes=50)
    elif args.network == 'ResNet18_mrf':
        model = ResNet18_mrf(BasicBlock, [2, 2, 2, 2], phase=1, num_classes=50)
    elif args.network == 'ResNet18_lrf':
        model = ResNet18_lrf(BasicBlock, [2, 2, 2, 2], phase=1, num_classes=50)


    if args.cuda:
        model.cuda()

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)
    #  optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)
    # exp_lr_scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=[50, 100, 150], gamma=0.1)
    exp_lr_scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=[70, 130, 150], gamma=0.1)

    trainDataset = WaveformDataset(trainPkl, window_size=66150, train_slices=args.train_slices, transform=ToTensor())

    train_loader = DataLoader(trainDataset, batch_size=args.batch_size, shuffle=True, num_workers=2)

    best_acc = 0.0
    for epoch in range(1, args.epochs + 1):
    # for epoch in range(1, 2):
        exp_lr_scheduler.step()

        train_p1(model, optimizer, train_loader, epoch)

        #  test and save the best model
        if epoch % 20 == 0:
            test_acc = test_p1(model, validPkl, fs=44100)
            if test_acc > best_acc:
                best_acc = test_acc
                best_model_wts = model.state_dict()

                model_name = '../model/' + args.network + '_fold' + str(foldNum) + '_ESC50_p1_v1.pkl'
                torch.save(model, model_name)
                print('model has been saved as: ' + model_name)


    # --------phase 2:----------
    # model_name = '../model/' + args.network + '_fold' + str(foldNum) + 'ESC10_p1_v1.pkl'
    # model = torch.load(model_name)
    # # model.load_state_dict(best_model_wts)
    # model.changePhase(2)
    # print('Phase 2')
    # layers = [model.conv1_1.parameters(),
    #           model.conv1_2.parameters(),
    #           model.conv1_3.parameters(),
    #           model.bn1_1.parameters(),
    #           model.bn1_2.parameters(),
    #           model.bn1_3.parameters(),
    #           model.conv2_1.parameters(),
    #           model.conv2_2.parameters(),
    #           model.conv2_3.parameters(),
    #           model.bn2_1.parameters(),
    #           model.bn2_2.parameters(),
    #           model.bn2_3.parameters()]
    #
    # for layer in layers:
    #     for param in layer:
    #         param.requiers_grad = False
    #
    #
    # model = M9_fixed_logmel(phase=2)
    # if args.cuda:
    #     model.cuda()
    #
    # trainDataset = FusionDataset(trainPkl, window_size=66150, train_slices=args.train_slices, transform=ToTensor2())
    #
    # train_loader = DataLoader(trainDataset, batch_size=args.batch_size, shuffle=True, num_workers=8)
    #
    # optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)
    # #  optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)
    # exp_lr_scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=[50, 100, 150], gamma=0.1)
    #
    # best_acc = 0
    # for epoch in range(1, args.epochs + 1):
    # # for epoch in range(1, 2):
    #     exp_lr_scheduler.step()
    #
    #     train_p2(model, optimizer, train_loader, epoch)
    #
    #     #  test and save the best model
    #     if epoch % 30 == 0:
    #         test_acc = test_p2(model, validPkl, fs=44100)
    #         if test_acc > best_acc:
    #             best_acc = test_acc
    #             model_name = '../model/' + args.network + '_fold' + str(foldNum) + 'ESC10_onePhase.pkl'
    #             torch.save(model, model_name)
    #             print('model has been saved as: ' + model_name)


def main():
    print(args.network)
    for fold_num in range(5):
        print('\nFold %d' % fold_num)
        trainPkl = '../data_wave_44100/fold' + str(fold_num) + '_train.cPickle'
        validPkl = '../data_wave_44100/fold' + str(fold_num) + '_test.cPickle'
        start = time.time()
        main_on_fold(fold_num, trainPkl, validPkl)
        print('time on fold: %fs' % (time.time() - start))


if __name__ == "__main__":
    main()
