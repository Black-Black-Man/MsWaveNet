""" usage:
    python main.py
    python main.py --network=dnn --mode=test --model='../model/dnn_mix.pkl'

"""
import argparse

from network import *
from data_process import *
from torchvision import datasets, transforms, models
import time
import os

# Training settings
parser = argparse.ArgumentParser(description='pytorch model')
parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                            help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=5, metavar='N',
                            help='input batch size for testing (default: 5)')
parser.add_argument('--epochs', type=int, default=80, metavar='N',
                            help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                            help='learning rate (default: 0.001)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                            help='SGD momentum (default: 0.9)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                            help='disables CUDA training')
parser.add_argument('--gpu', type=list, default=[4,5,6,7],
                            help='gpu device number')
parser.add_argument('--seed', type=int, default=777, metavar='S',
                            help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=20, metavar='N',
                            help='how many batches to wait before logging training status')
parser.add_argument('--model_save_interval', type=int, default=10, metavar='N',
                            help='how many epochs to wait before saving the model.')
parser.add_argument('--network', type=str, default='ELSTM',
                            help='EnvNet or EnvNet_mrf or EnvNet_lrf or EnvNet3D or EnvNetMultiScale')
parser.add_argument('--mode', type=str, default='train',
                            help='train or test')
parser.add_argument('--model', type=str, default='../model/dnn_MixNoise.pkl',
                            help='trained model path')
parser.add_argument('--num_slices', type=int, default=5,
                            help='slices number of one record divide into.')

os.environ['CUDA_VISIBLE_DEVICES'] = "0"

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

#  torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)
    #  torch.cuda.set_device(2)


def train(model, optimizer, train_loader, epoch):
#{{{
    model.train()
    #  start = time.time()
    for idx, (data, label) in enumerate(train_loader):

        #  reshape to torch.LongTensor of size 64
        label = label.resize_(label.size()[0])

        if args.cuda:
            data, label = data.cuda(), label.cuda()
        data, label = Variable(data), Variable(label)

        optimizer.zero_grad()

        # print data.size()
        output = model(data)
        # print(label)
        # print output
        # exit(0)
        loss = F.cross_entropy(output, label)
        #  loss = F.nll_loss(output, label)

        loss.backward()

        optimizer.step()


        if idx % args.log_interval == 0:

            pred = output.data.max(1)[1] # get the index of the max log-probability
            correct = pred.eq(label.data.view_as(pred)).sum()
            acc = 100.0 * correct / args.batch_size
            print('Train Epoch: {} [{}/{} ({:.0f}%)] '
                  'lr:{} Loss: {:.6f} '
                  'TrainAcc: {:.2f}'.format(
                    epoch, idx * len(data), len(train_loader.dataset),
                    100. * idx / len(train_loader),
                    optimizer.param_groups[0]['lr'], loss.data[0], acc))
            #  elapse = time.time() - start
            #  start = time.time()
            #  print('time/%dbatch: %fs' %(args.log_interval, elapse))

    # save model
    #  if args.network == 'densenet':
        #  torch.save(model, 'model/densenet.pkl')
        #  print('model has been saved as: model/densenet.pkl')
    #  elif args.network == 'dnn':
        #  torch.save(model, 'model/dnn.pkl')
        #  print('model has been saved as: model/dnn.pkl')
#}}}


def test(model, test_loader, train_loader):
#{{{
    model.eval()
    test_loss = 0
    correct = 0

    for data, label in test_loader:
        #  reshape to torch.LongTensor of size 64
        label = label.resize_(label.size()[0])


        for la in label:
            if la != label[0]:
                print('label in batch is not same.')
                exit(0)
        label = label[0]
        label = torch.LongTensor([label])

        if args.cuda:
            data, label = data.cuda(), label.cuda()
        data, label = Variable(data, volatile=True), Variable(label)

        output = model(data)
        output = torch.sum(output, dim=0, keepdim=True)
        # print output
        # print label
        # print key

        test_loss += F.cross_entropy(output, label).data[0] # sum up batch loss
        # print output
        # #  test_loss = F.nll_loss(output, label).data[0]
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        # print 'pred: ', pred
        # print 'label: ', label
        # print 'label2: ', label.data.view_as(pred)
        correct += pred.eq(label.data.view_as(pred)).sum()
        # print 'correct: ', correct
        # exit(0)
    test_loss /= len(test_loader.dataset)

    correct_train = 0
    for data, label in train_loader:
        #  reshape to torch.LongTensor of size 64
        label = label.resize_(label.size()[0])

        if args.cuda:
            data, label = data.cuda(), label.cuda()
        data, label = Variable(data, volatile=True), Variable(label)

        output = model(data)
        # print output
        # print label
        # print key

        # print output
        # #  test_loss = F.nll_loss(output, label).data[0]
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        # print 'pred: ', pred
        # print 'label: ', label
        # print 'label2: ', label.data.view_as(pred)
        correct_train += pred.eq(label.data.view_as(pred)).sum()
        # print 'correct: ', correct
        # exit(0)


    print('\nTest set: Average loss: {:.4f}, TestACC: {}/{} {:.2f}%, TrainACC: {}/{} {:.2f}%\n'.format(
        test_loss, correct, len(test_loader.dataset) / args.num_slices,
        100. * correct / len(test_loader.dataset) * args.num_slices,
        correct_train, len(train_loader.dataset),
        100. * correct_train / len(train_loader.dataset)))
#}}}


def adjust_learning_rate(optimizer, epoch):
    if epoch == 1:
        lr = args.lr
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
    if epoch == 50:
        lr = 0.001
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
    if epoch == 60:
        lr = 0.0001
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
    if epoch == 70:
        lr = 0.00001
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr


def main():
    model = ELSTM(in_dim=40, hidden_dim=512, n_layer=2, n_class=50)

    if args.cuda:
        model.cuda()

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=1e-6)
    #  optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)

    trainDataset = LogMelDataset('../segments_logmel/seg.train.cPickle', transform=ToTensor())
    testDataset = LogMelDataset('../segments_logmel/seg.test.cPickle', transform=ToTensor())

    train_loader = DataLoader(trainDataset, batch_size=args.batch_size, shuffle=True, num_workers=4)

    test_loader = DataLoader(testDataset, batch_size=args.test_batch_size, shuffle=False, num_workers=2)

    for epoch in range(1, args.epochs + 1):

        adjust_learning_rate(optimizer, epoch)


        # start = time.time()
        train(model, optimizer, train_loader, epoch)

        # print('time/epoch: %fs' % (time.time() - start))

        test(model, test_loader, train_loader)

        #  save model
        if epoch % args.model_save_interval == 0:
            model_name = '../model/'+args.network+'_v2_epoch'+str(epoch)+'.pkl'
            torch.save(model, model_name)
            print('model has been saved as: ' + model_name)
#}}}


if __name__ == "__main__":
    if args.mode == 'train':
        main()
    if args.mode == 'test':
        model_name = args.model
        model = torch.load(model_name)
        testDataset = WaveformDataset('../data_wave/ESC-50_test.cPickle', transform=ToTensor())
        test_loader = DataLoader(testDataset, batch_size=args.test_batch_size, shuffle=True, num_workers=1)
        test(model, test_loader)
