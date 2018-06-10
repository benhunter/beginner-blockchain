# http://ecomunsing.com/build-your-own-blockchain

import hashlib
import json
import sys
import random

random.seed(0)

def hashMe(msg=''):
    # wrap hashing algorithm
    if type(msg) != str:
        msg = json.dumps(msg, sort_keys=True) # sort to guarantee repeatability

    if sys.version_info.major == 2:
        return unicode(hashlib.sha256(msg).hexdigest(), 'utf-8')
    else:
        return hashlib.sha256(str(msg).encode('utf-8')).hexdigest()

def makeTransaction(maxValue=3):
    # create valid transactions in the range of (1,maxValue)
    sign = int(random.getrandbits(1)) * 2 - 1 # randomly choose -1 or 1
    amount = random.randint(1,maxValue)
    alicePays = sign * amount
    bobPays = -1 * alicePays

    # TODO have not checked for account overdraft
    return {'Alice':alicePays,'Bob':bobPays}


txnBuffer = [makeTransaction() for i in range(30)]
# print(txnBuffer)


def updateState(txn, state):
    '''
    Update the state.
    TODO validate the transaction
    :param txn: keyed dictionary for transfer amount
    :param state: keyed dictionary for account balance
    :return: updated state, with additional users added to state if needed
    '''

    state = state.copy() # working copy of data

    for key in txn:
        if key in state.keys():
            state[key] += txn[key]
        else:
            state[key] = txn[key]
    return state

def isValidTxn(txn, state):
    '''

    :param txn: keyed dictionary by account names
    :param state:
    :return:
    '''

    # check sum of deposits and withdrawals is 0
    if sum(txn.values()) is not 0:
        return False

    # check transaction is not overdraft
    for key in txn.keys():
        if key in state.keys():
            acctBalance = state[key]
        else:
            acctBalance = 0

        if (acctBalance + txn[key]) < 0:
            return False
    return True


def test_isValidTxn():
    state = {'Alice': 5, 'Bob': 5}

    assert(isValidTxn({'Alice': -3, 'Bob': 3}, state))  # Basic transaction- this works great!
    assert(not isValidTxn({'Alice': -4, 'Bob': 3}, state))  # But we can't create or destroy tokens!
    assert(not isValidTxn({'Alice': -6, 'Bob': 6}, state))  # We also can't overdraft our account.
    assert(isValidTxn({'Alice': -4, 'Bob': 2, 'Lisa': 2}, state))  # Creating new users is valid
    assert(not isValidTxn({'Alice': -4, 'Bob': 3, 'Lisa': 2}, state))  # But the same rules still apply!


def test_updateState():
    state = {'Alice': 5, 'Bob': 5}
    txn = {'Alice': -3, 'Bob': 3}
    if isValidTxn(txn, state):
        state = updateState(txn, state)
    assert(state == {'Alice': 2, 'Bob': 8})


state = {'Alice':50, 'Bob':50} # initial state
genesisBlockTxns = [state]
genesisBlockContents = {'blockNumber': 0, 'parentHash': None, 'txnCount': 1, 'txns':genesisBlockTxns}
genesisHash = hashMe(genesisBlockContents)
genesisBlock = {'hash':genesisHash, 'contents': genesisBlockContents}
genesisBlockStr = json.dumps(genesisBlock, sort_keys=True)

chain = [genesisBlock]


def makeBlock(txns, chain):
    parentBlock = chain[-1]
    parentHash = parentBlock['hash']
    blockNumber = parentBlock['contents']['blockNumber'] + 1
    txnCount = len(txns)
    blockContents = {'blockNumber': blockNumber, 'parentHash': parentHash, 'txnCount': len(txns), 'txns': txns}
    blockHash = hashMe(blockContents)
    block = {'hash':blockHash, 'contents':blockContents}

    return block

blockSizeLimit = 5 # transactions per block (arbitrary)
while len(txnBuffer) > 0:
    bufferStartSize = len(txnBuffer)

    # gather valid transactions for inclusion
    txnList = []
    while (len(txnBuffer) > 0) and (len(txnList) < blockSizeLimit):
        newTxn = txnBuffer.pop()
        validTxn = isValidTxn(newTxn, state)

        if validTxn:
            txnList.append(newTxn)
            state = updateState(newTxn, state)
        else:
            print('ignored transaction')
            sys.stdout.flush()
            continue

    myBlock = makeBlock(txnList, chain)
    chain.append(myBlock)

print(chain[0])
print(chain[1])

print(state)

def checkBlockHash(block):
    '''
    Raise exception if hash
    :param block:
    :return:
    '''
    expectedHash = hashMe(block['contents'])
    if block['hash'] != expectedHash:
        raise Exception('Hash does not match contents of block %s' % block['contents']['blockNumber'])
    return

def checkBlockValidity(block, parent, state):
    '''
    Check conditions:
        each transaction is valid
        block hash is valid for contents
        block number increments
        parent's block hash is accurate
    :param block:
    :param parent:
    :param state:
    :return:
    '''

    parentNumber = parent['contents']['blockNumber']
    parentHash = parent['hash']
    blockNumber = block['contents']['blockNumber']

    # check validity
    for txn in block['contents']['txns']:
        if isValidTxn(txn, state):
            state = updateState(txn, state)
        else:
            raise Exception('Invalid transaction in block %s: %s' % (blockNumber, txn))

    checkBlockHash(block)

    if blockNumber != (parentNumber + 1):
        raise Exception('Hash does not match contents of block %s, parent block %s' % (blockNumber, parentNumber))

    if block['contents']['parentHash'] != parentHash:
        raise Exception('Parent hash not accurate at block %s' % blockNumber)

    return state


def checkChain(chain):
    '''
    Check the chain from the genisis block (which gets special treatment)
        Check that all transactions are internally valid
        No overdrafts
        blocks are linked by hashes

    :param chain:
    :return: State as dict of accounts and balances or False if error detected.
    '''

    # check data type
    if type(chain) == str:
        try:
            chain = json.loads(chain)
            assert(type(chain)==list)
        except:
            return False
    elif type(chain) != list:
        return False

    state = {}

    # Check the genesis block
    for txn in chain[0]['contents']['txns']:
        # Is the update valid?
        state = updateState(txn, state)
    # Is the hash valid?
    checkBlockHash(chain[0])
    parent = chain[0]

    # Check the rest of the blocks
    for block in chain[1:]:
        state = checkBlockValidity(block, parent, state)
        parent = block

    return state

checkChain(chain)

chainAsText = json.dumps(chain, sort_keys=True)
checkChain(chainAsText)

import copy
nodeBchain = copy.copy(chain)
nodeBtxns = [makeTransaction() for i in range(5)]
newBlock = makeBlock(nodeBtxns, nodeBchain)

print('Blockchain on Node A is currently %s blocks long' % len(chain))

try:
    print('New Block received; checking validity...')
    state = checkBlockValidity(newBlock, chain[-1], state)
    chain.append(newBlock)
except:
    print('Invalid block; ignoring and waiting for the next block...')
print('Blockchain on Node A is now %s blocks long' % len(chain))



